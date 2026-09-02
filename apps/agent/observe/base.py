"""Index the ERC-8004 registries on Base into observations Cairn has witnessed.

Two registries are read on chain 8453:

    Identity    0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
    Reputation  0x8004BAa17C55a88189AE136b182e5fdA19dE9b63

Both are ERC-1967 proxies. The identity registry is an ERC-721, so an agent
resolves to an owner and a registration file through the standard views rather
than through a bespoke ABI.

On the feedback event's shape. Neither implementation is verified on Sourcify,
so its ABI is not published anywhere this indexer can fetch. The layout below
was derived from the wire: three indexed parameters (agent id, client address,
and the keccak of the first tag, confirmed by hashing the tag string back to the
topic), then eight non-indexed parameters. It decoded 549 of 549 live logs
cleanly, and `tests/test_observe_base.py` pins it against a captured log.

Three of those eight words are integers whose meaning is not published. They are
kept under `unresolved` rather than being given names like "score". Guessing a
field name and then judging an agent on it is exactly how a real counterparty
gets called `suspect` for no reason, and brief part 21 forbids it: absence of a
decoded field is not evidence of anything.

Every observation lands in the COLD journal through the phase 1 adapter, keyed
by a hash of the raw log, so a rerun over the same range writes nothing new.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from eth_abi.abi import decode as abi_decode
from web3 import Web3

from apps.agent.memory.store import (
    MemoryCapReachedError,
    MemoryStore,
    Observation,
    Store,
    counterparty_tenant,
    reviewer_tenant,
)
from apps.agent.observe.cursor import CursorStore

CHAIN = "base"
CHAIN_ID = 8453

IDENTITY_REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
REPUTATION_REGISTRY = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"

# Both registries were deployed within a block of each other.
REGISTRY_DEPLOY_BLOCK = 41_663_783

# The public Base endpoint rejects wider ranges with 413.
MAX_LOG_SPAN = 10_000

TOPIC_REGISTERED = Web3.keccak(text="Registered(uint256,string,address)").to_0x_hex()
TOPIC_METADATA_SET = Web3.keccak(text="MetadataSet(uint256,string,string,bytes)").to_0x_hex()

# Signature text unknown, see the module docstring. The topic is pinned as a
# literal because it cannot be derived from a name we do not have.
TOPIC_NEW_FEEDBACK = "0x6a4a61743519c9d648a14e6493f47dbe3ff1aa29e7785c96c8326a205e58febc"

FEEDBACK_TYPES = (
    "uint256",  # a sequential feedback id
    "uint256",  # unresolved
    "uint256",  # unresolved
    "string",  # tag1, repeated from the indexed topic
    "string",  # tag2
    "string",  # uri
    "string",  # file uri
    "uint256",  # unresolved
)

REGISTRATION_FETCH_TIMEOUT = 10
REGISTRATION_MAX_BYTES = 256 * 1024


@dataclass(frozen=True)
class LogRecord:
    """One raw log, before it means anything."""

    address: str
    topics: tuple[str, ...]
    data: bytes
    block_number: int
    tx_hash: str
    log_index: int


@dataclass(frozen=True)
class Registration:
    """An agent's off-chain registration file, if it could be read.

    `available` is the point of this type. A file Cairn could not fetch is not a
    file that says nothing, and the two must never collapse into each other.
    """

    uri: str
    available: bool
    content_hash: str | None = None
    body: dict[str, Any] | None = None


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: int
    owner: str | None
    token_uri: str | None
    registration: Registration | None


@dataclass
class IndexReport:
    from_block: int
    to_block: int
    agents: set[int] = field(default_factory=set)
    counterparties: set[str] = field(default_factory=set)
    reviewers: set[str] = field(default_factory=set)
    observations_written: int = 0
    duplicates_skipped: int = 0
    registrations_resolved: int = 0
    registrations_unavailable: int = 0
    stopped_at_cap: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "chain_id": CHAIN_ID,
            "from_block": self.from_block,
            "to_block": self.to_block,
            "blocks_scanned": max(0, self.to_block - self.from_block + 1),
            "agents": len(self.agents),
            "counterparty_dossiers": len(self.counterparties),
            "reviewer_dossiers": len(self.reviewers),
            "observations_written": self.observations_written,
            "duplicates_skipped": self.duplicates_skipped,
            "registrations_resolved": self.registrations_resolved,
            "registrations_unavailable": self.registrations_unavailable,
            "stopped_at_cap": self.stopped_at_cap,
        }


class ChainReader(Protocol):
    """The chain, narrowed to what the indexer needs, so tests can stand in."""

    def head_block(self) -> int: ...

    def get_logs(
        self, address: str, topic: str, from_block: int, to_block: int
    ) -> list[LogRecord]: ...

    def owner_of(self, agent_id: int) -> str | None: ...

    def token_uri(self, agent_id: int) -> str | None: ...


class Fetcher(Protocol):
    def fetch(self, url: str) -> bytes | None: ...


ERC721_VIEWS = [
    {
        "name": "ownerOf",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"type": "address"}],
    },
    {
        "name": "tokenURI",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"type": "string"}],
    },
]


class Web3Reader:
    """The real chain, over an archive-capable Base RPC."""

    def __init__(self, rpc_url: str) -> None:
        self._w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 60}))
        self._identity = self._w3.eth.contract(
            address=Web3.to_checksum_address(IDENTITY_REGISTRY), abi=ERC721_VIEWS
        )

    def head_block(self) -> int:
        return int(self._w3.eth.block_number)

    def get_logs(
        self, address: str, topic: str, from_block: int, to_block: int
    ) -> list[LogRecord]:
        raw = self._w3.eth.get_logs(
            {
                "address": Web3.to_checksum_address(address),
                "fromBlock": from_block,
                "toBlock": to_block,
                "topics": [topic],
            }
        )
        return [
            LogRecord(
                address=str(entry["address"]).lower(),
                topics=tuple(t.to_0x_hex() for t in entry["topics"]),
                data=bytes(entry["data"]),
                block_number=int(entry["blockNumber"]),
                tx_hash=entry["transactionHash"].to_0x_hex(),
                log_index=int(entry["logIndex"]),
            )
            for entry in raw
        ]

    def owner_of(self, agent_id: int) -> str | None:
        try:
            return str(self._identity.functions.ownerOf(agent_id).call()).lower()
        # A burned or absent token is not an error here, it is an unknown owner.
        except Exception:
            return None

    def token_uri(self, agent_id: int) -> str | None:
        try:
            uri = str(self._identity.functions.tokenURI(agent_id).call())
        # An agent may simply not set a registration file.
        except Exception:
            return None
        return uri or None


class HttpFetcher:
    """Fetches registration files, and returns None rather than raising.

    A registration file is third-party content named by an on-chain string, so
    the scheme is checked, the read is bounded, and a failure is reported as
    "not available" rather than as an empty document.
    """

    def fetch(self, url: str) -> bytes | None:
        if not url.startswith(("http://", "https://")):
            return None
        try:
            # S310 on both calls: the scheme is checked above, so file: and
            # custom schemes cannot reach here from an on-chain string.
            request = urllib.request.Request(  # noqa: S310
                url, headers={"User-Agent": "cairn-indexer"}
            )
            opened = urllib.request.urlopen(  # noqa: S310
                request, timeout=REGISTRATION_FETCH_TIMEOUT
            )
            with opened as response:
                return bytes(response.read(REGISTRATION_MAX_BYTES))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return None


def evidence_hash(log: LogRecord) -> str:
    """A stable hash of the raw evidence, and the idempotency key.

    Covers the log's identity and its contents, so the same log rehashes to the
    same value on a rerun, and a reorg that changes the payload does not.
    """
    digest = hashlib.sha256()
    digest.update(f"{CHAIN_ID}|{log.address}|{log.tx_hash}|{log.log_index}|".encode())
    for topic in log.topics:
        digest.update(topic.encode())
    digest.update(log.data)
    return f"sha256:{digest.hexdigest()}"


def _topic_to_int(topic: str) -> int:
    return int(topic, 16)


def _topic_to_address(topic: str) -> str:
    return "0x" + topic[-40:]


@dataclass(frozen=True)
class Feedback:
    agent_id: int
    client: str
    tag_hash: str
    feedback_id: int
    tag1: str
    tag2: str
    uri: str
    file_uri: str
    unresolved: tuple[int, int, int]


def decode_feedback(log: LogRecord) -> Feedback | None:
    """Decode one feedback log, or None if it does not match the known layout."""
    if len(log.topics) < 4 or log.topics[0].lower() != TOPIC_NEW_FEEDBACK:
        return None
    try:
        values = abi_decode(list(FEEDBACK_TYPES), log.data)
    # An unknown variant is skipped rather than guessed at.
    except Exception:
        return None
    return Feedback(
        agent_id=_topic_to_int(log.topics[1]),
        client=_topic_to_address(log.topics[2]),
        tag_hash=log.topics[3],
        feedback_id=int(values[0]),
        tag1=str(values[3]),
        tag2=str(values[4]),
        uri=str(values[5]),
        file_uri=str(values[6]),
        unresolved=(int(values[1]), int(values[2]), int(values[7])),
    )


def decode_registered(log: LogRecord) -> tuple[int, str] | None:
    """Decode Registered(uint256 indexed agentId, string tokenURI, address indexed owner)."""
    if len(log.topics) < 3 or log.topics[0].lower() != TOPIC_REGISTERED:
        return None
    return _topic_to_int(log.topics[1]), _topic_to_address(log.topics[2])


class BaseIndexer:
    """Reads the registries and writes what it witnessed into the journal."""

    def __init__(
        self,
        store: Store,
        reader: ChainReader,
        cursor: CursorStore,
        fetcher: Fetcher | None = None,
        *,
        stream: str = "erc8004",
        resolve_registrations: bool = True,
    ) -> None:
        self._store = store
        self._reader = reader
        self._cursor = cursor
        self._fetcher = fetcher
        self._stream = stream
        self._resolve = resolve_registrations
        self._identities: dict[int, AgentIdentity] = {}
        self._seen: dict[str, set[str]] = {}

    # ---- idempotency ------------------------------------------------------

    def _already_recorded(self, tenant: str, content_hash: str) -> bool:
        """Observations are facts, so the journal itself is the seen-set.

        Loaded once per dossier per run rather than per write, which keeps a
        rerun over a scanned range from being quadratic.
        """
        if tenant not in self._seen:
            with self._store.use(tenant):
                self._seen[tenant] = {
                    str(row.get("content_hash")) for row in self._store.observations()
                }
        return content_hash in self._seen[tenant]

    def _remember(self, tenant: str, content_hash: str) -> None:
        self._seen.setdefault(tenant, set()).add(content_hash)

    def _write(self, tenant: str, obs: Observation, report: IndexReport) -> bool:
        if self._already_recorded(tenant, obs.content_hash):
            report.duplicates_skipped += 1
            return False
        with self._store.use(tenant):
            self._store.record_observation(obs)
        self._remember(tenant, obs.content_hash)
        report.observations_written += 1
        return True

    # ---- identity ---------------------------------------------------------

    def identity(self, agent_id: int, report: IndexReport) -> AgentIdentity:
        cached = self._identities.get(agent_id)
        if cached is not None:
            return cached

        owner = self._reader.owner_of(agent_id)
        uri = self._reader.token_uri(agent_id)
        registration: Registration | None = None

        if uri and self._resolve and self._fetcher is not None:
            raw = self._fetcher.fetch(uri)
            if raw is None:
                registration = Registration(uri=uri, available=False)
                report.registrations_unavailable += 1
            else:
                body: dict[str, Any] | None = None
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                    body = parsed if isinstance(parsed, dict) else None
                except (UnicodeDecodeError, json.JSONDecodeError):
                    body = None
                registration = Registration(
                    uri=uri,
                    available=True,
                    content_hash=f"sha256:{hashlib.sha256(raw).hexdigest()}",
                    body=body,
                )
                report.registrations_resolved += 1
        elif uri:
            registration = Registration(uri=uri, available=False)

        found = AgentIdentity(
            agent_id=agent_id, owner=owner, token_uri=uri, registration=registration
        )
        self._identities[agent_id] = found
        return found

    @staticmethod
    def _subject(found: AgentIdentity) -> str:
        """The dossier an agent's observations belong to."""
        return found.owner or f"agent-{found.agent_id}"

    # ---- the scan ---------------------------------------------------------

    def run(
        self,
        *,
        from_block: int | None = None,
        to_block: int | None = None,
        max_observations: int | None = None,
    ) -> IndexReport:
        head = self._reader.head_block()
        start = from_block if from_block is not None else self._resume_from()
        end = min(to_block if to_block is not None else head, head)
        report = IndexReport(from_block=start, to_block=end)

        block = start
        while block <= end:
            chunk_end = min(block + MAX_LOG_SPAN - 1, end)
            try:
                self._scan_chunk(block, chunk_end, report)
            except MemoryCapReachedError:
                # The indexed set is bounded by what the free tier holds. Stop
                # where it filled up and say so, rather than truncating quietly.
                report.stopped_at_cap = True
                report.to_block = chunk_end
                break
            self._cursor.set(self._stream, chunk_end)
            report.to_block = chunk_end
            if max_observations is not None and report.observations_written >= max_observations:
                break
            block = chunk_end + 1

        return report

    def _resume_from(self) -> int:
        last = self._cursor.get(self._stream)
        return REGISTRY_DEPLOY_BLOCK if last is None else last + 1

    def _scan_chunk(self, from_block: int, to_block: int, report: IndexReport) -> None:
        for log in self._reader.get_logs(
            REPUTATION_REGISTRY, TOPIC_NEW_FEEDBACK, from_block, to_block
        ):
            self._ingest_feedback(log, report)

        for log in self._reader.get_logs(
            IDENTITY_REGISTRY, TOPIC_REGISTERED, from_block, to_block
        ):
            self._ingest_registration(log, report)

    def _ingest_registration(self, log: LogRecord, report: IndexReport) -> None:
        decoded = decode_registered(log)
        if decoded is None:
            return
        agent_id, owner = decoded
        report.agents.add(agent_id)

        found = self.identity(agent_id, report)
        subject = found.owner or owner
        tenant = counterparty_tenant(CHAIN, subject)
        report.counterparties.add(tenant)

        registration = found.registration
        obs = Observation(
            kind="erc8004_registration",
            pattern="registered-on-erc8004",
            source=f"{CHAIN}:{IDENTITY_REGISTRY}",
            content_hash=evidence_hash(log),
            occurred_at=datetime.now(UTC),
            body={
                "agent_id": agent_id,
                "owner": owner,
                "token_uri": found.token_uri,
                "block_number": log.block_number,
                "tx_hash": log.tx_hash,
                "registration_available": bool(registration and registration.available),
                "registration_hash": registration.content_hash if registration else None,
            },
        )
        self._write(tenant, obs, report)

    def _ingest_feedback(self, log: LogRecord, report: IndexReport) -> None:
        decoded = decode_feedback(log)
        if decoded is None:
            return
        report.agents.add(decoded.agent_id)

        found = self.identity(decoded.agent_id, report)
        subject = self._subject(found)
        subject_tenant = counterparty_tenant(CHAIN, subject)
        claimant_tenant = reviewer_tenant(decoded.client)
        report.counterparties.add(subject_tenant)
        report.reviewers.add(claimant_tenant)

        content_hash = evidence_hash(log)
        common: dict[str, Any] = {
            "agent_id": decoded.agent_id,
            "client": decoded.client,
            "feedback_id": decoded.feedback_id,
            "tag1": decoded.tag1,
            "tag2": decoded.tag2,
            "uri": decoded.uri,
            "file_uri": decoded.file_uri,
            "block_number": log.block_number,
            "tx_hash": log.tx_hash,
            # Named nothing, because their meaning is not published anywhere we
            # can check. Kept so phase 3 can use them once it is.
            "unresolved": list(decoded.unresolved),
        }

        # What was claimed about the counterparty.
        self._write(
            subject_tenant,
            Observation(
                kind="erc8004_feedback",
                pattern=f"feedback-tagged:{decoded.tag1}" if decoded.tag1 else "feedback-untagged",
                source=f"{CHAIN}:{REPUTATION_REGISTRY}",
                content_hash=content_hash,
                occurred_at=datetime.now(UTC),
                body=common,
                reviewer=decoded.client,
            ),
            report,
        )

        # And the same event from the claimant's side, which is what reviewer
        # weighting is later computed over. The claimant's dossier records that
        # a claim was made and what evidences it, not a second copy of the
        # payload: both sides key off the same evidence hash, and the free tier
        # caps the database at 5,242,880 bytes.
        self._write(
            claimant_tenant,
            Observation(
                kind="erc8004_claim",
                pattern=f"claims-about:{decoded.agent_id}",
                source=f"{CHAIN}:{REPUTATION_REGISTRY}",
                content_hash=content_hash,
                occurred_at=datetime.now(UTC),
                body={
                    "agent_id": decoded.agent_id,
                    "client": decoded.client,
                    "feedback_id": decoded.feedback_id,
                    "tag1": decoded.tag1,
                    "block_number": log.block_number,
                    "tx_hash": log.tx_hash,
                },
                reviewer=decoded.client,
            ),
            report,
        )


def main(argv: Sequence[str] | None = None) -> int:
    import os

    parser = argparse.ArgumentParser(description="Index the ERC-8004 registries on Base.")
    parser.add_argument(
        "--rpc", default=os.environ.get("BASE_RPC_URL") or "https://mainnet.base.org"
    )
    parser.add_argument("--db", default=os.environ.get("SIBYL_DB") or "data/memory.db")
    parser.add_argument("--cursor-db", default="data/indexer.db")
    parser.add_argument("--from-block", type=int, default=None)
    parser.add_argument("--to-block", type=int, default=None)
    parser.add_argument(
        "--blocks", type=int, default=None, help="scan this many blocks back from head"
    )
    parser.add_argument("--max-observations", type=int, default=None)
    parser.add_argument("--no-registrations", action="store_true")
    parser.add_argument(
        "--bootstrap", action="store_true", help="scan from the registry deployment"
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    reader = Web3Reader(args.rpc)
    store = MemoryStore.open(args.db)
    cursor = CursorStore(args.cursor_db)

    from_block = args.from_block
    if args.bootstrap:
        from_block = REGISTRY_DEPLOY_BLOCK
    if args.blocks is not None and from_block is None:
        from_block = max(REGISTRY_DEPLOY_BLOCK, reader.head_block() - args.blocks)

    indexer = BaseIndexer(
        store,
        reader,
        cursor,
        HttpFetcher(),
        resolve_registrations=not args.no_registrations,
    )
    try:
        report = indexer.run(
            from_block=from_block,
            to_block=args.to_block,
            max_observations=args.max_observations,
        )
    finally:
        store.close()
        cursor.close()

    summary = report.as_dict()
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        width = max(len(k) for k in summary)
        for key, value in summary.items():
            print(f"  {key.ljust(width)}   {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
