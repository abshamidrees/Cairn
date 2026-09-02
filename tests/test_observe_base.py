"""Tests for the Base indexer.

Offline and deterministic. The chain is stubbed, but the logs are not: the
fixtures in tests/fixtures/base_logs.json were captured from Base mainnet, so
the decoder is pinned against bytes a real contract emitted rather than against
bytes this repo encoded for itself.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from apps.agent.memory.store import MemoryStore, counterparty_tenant, reviewer_tenant
from apps.agent.observe.base import (
    CHAIN,
    TOPIC_NEW_FEEDBACK,
    BaseIndexer,
    IndexReport,
    LogRecord,
    Registration,
    decode_feedback,
    decode_registered,
    evidence_hash,
)
from apps.agent.observe.cursor import CursorStore

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "base_logs.json").read_text(encoding="utf-8")
)


def log_from(name: str) -> LogRecord:
    raw = FIXTURES[name]
    return LogRecord(
        address=raw["address"],
        topics=tuple(raw["topics"]),
        data=bytes.fromhex(raw["data"]),
        block_number=raw["block_number"],
        tx_hash=raw["tx_hash"],
        log_index=raw["log_index"],
    )


class StubChain:
    """A chain that returns exactly the logs a test hands it."""

    def __init__(self, logs: dict[str, list[LogRecord]], head: int = 50_800_000) -> None:
        self._logs = logs
        self._head = head
        self.owner_calls = 0

    def head_block(self) -> int:
        return self._head

    def get_logs(
        self, address: str, topic: str, from_block: int, to_block: int
    ) -> list[LogRecord]:
        return [
            entry
            for entry in self._logs.get(topic, [])
            if from_block <= entry.block_number <= to_block
        ]

    def owner_of(self, agent_id: int) -> str | None:
        self.owner_calls += 1
        return f"0x{agent_id:040x}"

    def token_uri(self, agent_id: int) -> str | None:
        return f"https://example.invalid/{agent_id}.json"


class DeadFetcher:
    """Every registration file is unreachable."""

    def fetch(self, url: str) -> bytes | None:
        del url
        return None


class LiveFetcher:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def fetch(self, url: str) -> bytes | None:
        del url
        return self._payload


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MemoryStore]:
    s = MemoryStore.open(tmp_path / "memory.db")
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def cursor(tmp_path: Path) -> Iterator[CursorStore]:
    c = CursorStore(tmp_path / "indexer.db")
    try:
        yield c
    finally:
        c.close()


# ---- decoding ------------------------------------------------------------


def test_feedback_decodes_from_a_real_captured_log() -> None:
    decoded = decode_feedback(log_from("new_feedback"))
    assert decoded is not None
    assert decoded.agent_id > 0
    assert decoded.client.startswith("0x")
    assert len(decoded.client) == 42
    # tag1 is emitted twice, once hashed into a topic and once in the data. If
    # the derived layout were wrong these would not agree.
    from web3 import Web3

    assert Web3.keccak(text=decoded.tag1).to_0x_hex() == decoded.tag_hash


def test_registered_decodes_from_a_real_captured_log() -> None:
    decoded = decode_registered(log_from("registered"))
    assert decoded is not None
    agent_id, owner = decoded
    assert agent_id > 0
    assert owner.startswith("0x")
    assert len(owner) == 42


def test_decoders_reject_a_log_they_do_not_recognise() -> None:
    """A shape the indexer cannot read is skipped, never guessed at."""
    wrong = LogRecord(
        address="0xdead",
        topics=("0x" + "11" * 32, "0x" + "22" * 32),
        data=b"\x00" * 32,
        block_number=1,
        tx_hash="0xabc",
        log_index=0,
    )
    assert decode_feedback(wrong) is None
    assert decode_registered(wrong) is None


def test_evidence_hash_is_stable_and_content_sensitive() -> None:
    log = log_from("new_feedback")
    assert evidence_hash(log) == evidence_hash(log)

    tampered = LogRecord(
        address=log.address,
        topics=log.topics,
        data=log.data + b"\x01",
        block_number=log.block_number,
        tx_hash=log.tx_hash,
        log_index=log.log_index,
    )
    assert evidence_hash(tampered) != evidence_hash(log)


# ---- writing through the adapter ----------------------------------------


def test_feedback_lands_in_both_the_subject_and_the_claimant_dossier(
    store: MemoryStore, cursor: CursorStore
) -> None:
    log = log_from("new_feedback")
    decoded = decode_feedback(log)
    assert decoded is not None

    chain = StubChain({TOPIC_NEW_FEEDBACK: [log]})
    indexer = BaseIndexer(store, chain, cursor, DeadFetcher())
    report = indexer.run(from_block=log.block_number, to_block=log.block_number)

    assert report.observations_written == 2

    subject = counterparty_tenant(CHAIN, f"0x{decoded.agent_id:040x}")
    with store.use(subject):
        rows = store.observations()
        assert len(rows) == 1
        assert rows[0]["kind"] == "erc8004_feedback"
        assert rows[0]["body"]["agent_id"] == decoded.agent_id

    with store.use(reviewer_tenant(decoded.client)):
        rows = store.observations()
        assert len(rows) == 1
        assert rows[0]["kind"] == "erc8004_claim"


def test_a_rerun_over_the_same_range_writes_nothing_new(
    store: MemoryStore, cursor: CursorStore
) -> None:
    log = log_from("new_feedback")
    chain = StubChain({TOPIC_NEW_FEEDBACK: [log]})

    first = BaseIndexer(store, chain, cursor, DeadFetcher()).run(
        from_block=log.block_number, to_block=log.block_number
    )
    assert first.observations_written == 2
    assert first.duplicates_skipped == 0

    # A fresh indexer, so the seen-set is rebuilt from the journal rather than
    # from anything held in the previous run's memory.
    second = BaseIndexer(store, chain, cursor, DeadFetcher()).run(
        from_block=log.block_number, to_block=log.block_number
    )
    assert second.observations_written == 0
    assert second.duplicates_skipped == 2


def test_the_cursor_resumes_where_the_last_run_stopped(
    store: MemoryStore, cursor: CursorStore
) -> None:
    log = log_from("new_feedback")
    chain = StubChain({TOPIC_NEW_FEEDBACK: [log]}, head=log.block_number + 5)

    BaseIndexer(store, chain, cursor, DeadFetcher()).run(
        from_block=log.block_number, to_block=log.block_number
    )
    assert cursor.get("erc8004") == log.block_number

    # With no explicit range the next run starts after the recorded block.
    resumed = BaseIndexer(store, chain, cursor, DeadFetcher()).run()
    assert resumed.from_block == log.block_number + 1
    assert resumed.observations_written == 0


def test_max_observations_stops_the_scan(store: MemoryStore, cursor: CursorStore) -> None:
    log = log_from("new_feedback")
    chain = StubChain({TOPIC_NEW_FEEDBACK: [log]})
    report = BaseIndexer(store, chain, cursor, DeadFetcher()).run(
        from_block=log.block_number, to_block=log.block_number + 100_000, max_observations=1
    )
    assert report.observations_written <= 2
    assert report.to_block < log.block_number + 100_000


# ---- part 21, absence is never evidence ---------------------------------


def test_an_unreachable_registration_file_is_recorded_as_unavailable(
    store: MemoryStore, cursor: CursorStore
) -> None:
    log = log_from("registered")
    decoded = decode_registered(log)
    assert decoded is not None

    chain = StubChain({log.topics[0]: [log]})
    indexer = BaseIndexer(store, chain, cursor, DeadFetcher())
    report = indexer.run(from_block=log.block_number, to_block=log.block_number)

    assert report.registrations_unavailable == 1
    assert report.registrations_resolved == 0

    tenant = counterparty_tenant(CHAIN, f"0x{decoded[0]:040x}")
    with store.use(tenant):
        rows = store.observations()
        assert len(rows) == 1
        body = rows[0]["body"]
        # Unavailable, and explicitly so. Never an empty document standing in
        # for a document that says nothing.
        assert body["registration_available"] is False
        assert body["registration_hash"] is None


def test_a_resolved_registration_file_is_hashed(
    store: MemoryStore, cursor: CursorStore
) -> None:
    log = log_from("registered")
    chain = StubChain({log.topics[0]: [log]})
    payload = json.dumps({"name": "an agent", "services": []}).encode()

    indexer = BaseIndexer(store, chain, cursor, LiveFetcher(payload))
    report = indexer.run(from_block=log.block_number, to_block=log.block_number)

    assert report.registrations_resolved == 1
    assert report.registrations_unavailable == 0

    decoded = decode_registered(log)
    assert decoded is not None
    with store.use(counterparty_tenant(CHAIN, f"0x{decoded[0]:040x}")):
        body = store.observations()[0]["body"]
        assert body["registration_available"] is True
        assert str(body["registration_hash"]).startswith("sha256:")


def test_registration_is_not_fetched_when_resolution_is_off(
    store: MemoryStore, cursor: CursorStore
) -> None:
    log = log_from("registered")
    chain = StubChain({log.topics[0]: [log]})
    indexer = BaseIndexer(
        store, chain, cursor, LiveFetcher(b"{}"), resolve_registrations=False
    )
    report = indexer.run(from_block=log.block_number, to_block=log.block_number)
    assert report.registrations_resolved == 0


def test_unresolved_feedback_words_are_kept_but_never_named() -> None:
    """Three integers in the event have no published meaning.

    They are carried so phase 3 can use them once the ABI is known, and they are
    not labelled "score", because judging a real agent on a guessed field is how
    an auditor accuses the wrong party.
    """
    decoded = decode_feedback(log_from("new_feedback"))
    assert decoded is not None
    assert len(decoded.unresolved) == 3
    assert all(isinstance(v, int) for v in decoded.unresolved)


def test_report_counts_are_consistent() -> None:
    report = IndexReport(from_block=10, to_block=19)
    assert report.as_dict()["blocks_scanned"] == 10
    assert report.as_dict()["chain_id"] == 8453


def test_registration_availability_is_explicit_in_the_type() -> None:
    unavailable = Registration(uri="https://x.invalid/a.json", available=False)
    assert unavailable.content_hash is None
    assert unavailable.body is None
