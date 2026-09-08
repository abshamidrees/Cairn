"""Register Firsthand as an agent on the ERC-8004 Identity Registry.

The registry at `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` on Base is a UUPS
proxy. Its implementation, `0x7274e874CA62410a93Bd8bf61c69d8045E399c02`, is
verified on Basescan as `IdentityRegistryUpgradeable`, solc 0.8.24, exact match,
and `packages/chain/abi/identity-registry.json` is taken from that verified ABI.

Nothing here reconstructs a selector. The last time a signature was guessed, for
the reputation registry, the selector on the wire matched nothing we could
rebuild and the write was abandoned rather than sent blind. The difference this
time is that the ABI is published, so `register(string)` is read rather than
inferred.

Two independent things agree on the shape. The verified ABI declares
`Registered(uint256 indexed agentId, string agentURI, address indexed owner)`,
and `observe/base.py` has been decoding that exact signature off the wire for
549 of 549 live logs since the indexer was built.

Encoding is separated from sending on purpose: `encode` is pure and tested, so
what goes on chain is checkable offline before anyone spends gas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.contract import Contract
from web3.types import TxReceipt

from apps.agent.memory.store import MemoryCapReachedError, Store

ABI_PATH = Path(__file__).resolve().parent.parent.parent.parent / (
    "packages/chain/abi/identity-registry.json"
)

BASE_CHAIN_ID = 8453

#: The proxy. Calls go here; the ABI comes from the implementation behind it.
IDENTITY_REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"

#: The verified implementation the ABI was read from, recorded so a reader can
#: check the source of the shape rather than trusting this file.
IDENTITY_IMPLEMENTATION = "0x7274e874CA62410a93Bd8bf61c69d8045E399c02"

#: Registering with no URI is legal on this contract and says nothing. A
#: registration that cannot be resolved to a description is a row, not a claim.
MIN_URI_LENGTH = 8


class RegistrationError(RuntimeError):
    """The registration could not be sent, or would have said nothing."""


class RegistrationRecordError(RegistrationError):
    """Registered on chain, but the dossier could not be updated to say so.

    Carries the hash. At this point the transaction is mined and paid for and
    the hash is the only thing the money bought. The same failure on the
    attestation path once discarded a landed transaction and left the chain as
    the only place it existed.
    """

    def __init__(self, message: str, *, tx_hash: str) -> None:
        super().__init__(message)
        self.tx_hash = tx_hash


@dataclass(frozen=True)
class RegistrationCall:
    """Exactly what goes on chain. Pure data, so it can be checked offline."""

    agent_uri: str

    def as_args(self) -> tuple[str]:
        return (self.agent_uri,)

    def as_payload(self) -> dict[str, Any]:
        return {
            "contract": IDENTITY_REGISTRY,
            "chain_id": BASE_CHAIN_ID,
            "function": "register(string)",
            "agent_uri": self.agent_uri,
        }


def load_abi() -> list[dict[str, Any]]:
    """The verified ABI, read from disk rather than fetched at run time."""
    decoded: Any = json.loads(ABI_PATH.read_text(encoding="utf-8"))
    if not isinstance(decoded, list):
        raise RegistrationError(f"{ABI_PATH} does not hold an ABI array")
    return decoded


def encode(agent_uri: str) -> RegistrationCall:
    """Turn an agent card URL into the call that registers it.

    Refuses what the registry would happily accept but nobody could read: an
    empty URI, or one that is not resolvable over http. The registry does not
    care, and a registration pointing at nothing is exactly the unevidenced
    claim this project exists to argue against.
    """
    uri = agent_uri.strip()
    if len(uri) < MIN_URI_LENGTH:
        raise RegistrationError("refusing to register an empty agent uri")
    if not uri.startswith(("https://", "ipfs://")):
        raise RegistrationError(
            f"refusing to register a uri a reader cannot fetch: {uri!r}. "
            "The indexed set holds https and ipfs; anything else resolves for nobody"
        )
    return RegistrationCall(agent_uri=uri)


def record_registration(store: Store, agent_id: int, tx_hash: str, agent_uri: str) -> None:
    """Note in Firsthand's own dossier that it registered, and as what.

    Firsthand keeps a record on itself for the same reason it keeps one on
    everybody else: the claim should be checkable against something it holds.
    """
    from apps.agent.memory.store import SELF_TENANT

    with store.use(SELF_TENANT):
        store.assert_fact(
            "registration",
            "erc8004",
            f"{agent_id}",
            observation_id=tx_hash,
        )
        store.put_reference(
            "erc8004-registration",
            {
                "agent_id": agent_id,
                "agent_uri": agent_uri,
                "tx_hash": f"0x{tx_hash.removeprefix('0x')}",
                "registry": IDENTITY_REGISTRY,
                "chain_id": BASE_CHAIN_ID,
            },
        )


class Registrar:
    """Signs and sends. Everything it needs is passed in, nothing is ambient."""

    def __init__(self, w3: Web3, private_key: str) -> None:
        if not private_key:
            raise RegistrationError("no key: set FIRSTHAND_ATTESTOR_KEY")
        self._w3 = w3
        self._account = w3.eth.account.from_key(private_key)
        self._abi = load_abi()

    @property
    def address(self) -> str:
        return str(self._account.address)

    def register(self, call: RegistrationCall, *, store: Store | None = None) -> tuple[str, int]:
        """Send the registration. Returns (transaction hash, agent id)."""
        contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(IDENTITY_REGISTRY), abi=self._abi
        )
        # The overload is named explicitly. Three functions share the name
        # `register` on this contract and web3 will not choose between them.
        fn = contract.get_function_by_signature("register(string)")(*call.as_args())
        tx = fn.build_transaction(
            {
                "from": self._account.address,
                "nonce": self._w3.eth.get_transaction_count(self._account.address),
                "chainId": BASE_CHAIN_ID,
            }
        )
        signed = self._account.sign_transaction(tx)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        published = tx_hash.hex()

        agent_id = self._agent_id_from(contract, receipt)

        if store is not None:
            try:
                record_registration(store, agent_id, published, call.agent_uri)
            except MemoryCapReachedError as exc:
                raise RegistrationRecordError(str(exc), tx_hash=published) from exc
        return published, agent_id

    def _agent_id_from(self, contract: Contract, receipt: TxReceipt) -> int:
        """Read the id out of the Registered event the contract emitted.

        The id is assigned by the registry, so it is read back rather than
        assumed. A receipt without the event means the write did not do what
        this script says it does, and that is worth failing on.
        """
        events = contract.events.Registered().process_receipt(receipt)
        if not events:
            raise RegistrationError(
                "the receipt carried no Registered event, so no agent id was assigned"
            )
        agent_id: int = events[0]["args"]["agentId"]
        return agent_id


def registrar_from_env(rpc_url: str | None = None) -> Registrar:
    """Build a Registrar from the environment. The key is never logged."""
    import os

    from apps.agent.publish.attest import _usable_rpc

    url = rpc_url or _usable_rpc(os.environ.get("BASE_RPC_URL")) or "https://mainnet.base.org"
    key = os.environ.get("FIRSTHAND_ATTESTOR_KEY", "")
    return Registrar(Web3(Web3.HTTPProvider(url)), key)
