"""Tests for the ERC-8004 registration encoding.

Nothing here touches a chain or a key. `encode` is pure, which is the point of
separating it: what goes on Base is checkable offline, before anyone spends gas
registering a URI that resolves for nobody.

The signature is not asserted from memory. It is read out of the ABI committed
at `packages/chain/abi/identity-registry.json`, which was taken from the
verified implementation behind the registry proxy.
"""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext

import pytest
from eth_utils import keccak

from apps.agent.memory.store import MemoryCapReachedError
from apps.agent.publish.register import (
    BASE_CHAIN_ID,
    IDENTITY_REGISTRY,
    RegistrationError,
    RegistrationRecordError,
    encode,
    load_abi,
    record_registration,
)

CARD = "https://firsthand-iota.vercel.app/.well-known/agent-card.json"


# ---- the encoded call ----------------------------------------------------


def test_the_agent_uri_survives_encoding_unchanged() -> None:
    assert encode(CARD).as_args() == (CARD,)


def test_surrounding_whitespace_is_stripped() -> None:
    """A URI pasted from a terminal should not register with a newline in it."""
    assert encode(f"  {CARD}\n").agent_uri == CARD


def test_the_payload_names_the_chain_and_the_registry() -> None:
    payload = encode(CARD).as_payload()

    assert payload["chain_id"] == BASE_CHAIN_ID
    assert payload["contract"] == IDENTITY_REGISTRY
    assert payload["function"] == "register(string)"


def test_an_empty_uri_is_refused() -> None:
    with pytest.raises(RegistrationError, match="empty"):
        encode("   ")


@pytest.mark.parametrize(
    "uri",
    [
        "ftp://firsthand.example/card.json",
        "agent-card.json",
        # Real registrations in the indexed set use this, and nothing can
        # fetch it: the description lives in the URI instead of behind it.
        'data:application/json,{"name":"Codex Solidity Invaders","active":true}',
    ],
)
def test_a_uri_a_reader_cannot_fetch_is_refused(uri: str) -> None:
    """The registry accepts anything. A row nobody can resolve is not a claim."""
    with pytest.raises(RegistrationError, match="cannot fetch"):
        encode(uri)


def test_ipfs_is_accepted_because_the_indexed_set_holds_it() -> None:
    uri = "ipfs://bafkreifsufdmfr7ym6hwiepx7bjofybqzsgvvwxz5j6cwujvarl5o3mlly"
    assert encode(uri).agent_uri == uri


# ---- the ABI, and the signature it declares ------------------------------


def test_the_committed_abi_declares_the_overload_we_call() -> None:
    """Read from the ABI rather than asserted from memory, so a wrong file fails."""
    abi = load_abi()
    registers = [
        entry
        for entry in abi
        if entry.get("type") == "function" and entry.get("name") == "register"
    ]
    signatures = {
        f"register({','.join(i['type'] for i in entry['inputs'])})" for entry in registers
    }

    assert "register(string)" in signatures
    one = next(e for e in registers if [i["type"] for i in e["inputs"]] == ["string"])
    assert one["inputs"][0]["name"] == "agentURI"
    assert [o["type"] for o in one["outputs"]] == ["uint256"]
    assert one["stateMutability"] == "nonpayable"


def test_the_registered_event_matches_what_the_indexer_decodes() -> None:
    """Two independent sources agree, so neither is being taken on trust.

    `observe/base.py` has decoded this signature off the wire for every live log
    it has read. The ABI here came from the verified implementation. If they
    ever disagree, one of them is wrong and this fails rather than the indexer
    quietly missing registrations.
    """
    from apps.agent.observe.base import TOPIC_REGISTERED

    abi = load_abi()
    event = next(e for e in abi if e.get("type") == "event" and e["name"] == "Registered")
    signature = f"Registered({','.join(i['type'] for i in event['inputs'])})"

    assert signature == "Registered(uint256,string,address)"
    assert TOPIC_REGISTERED.lower() == f"0x{keccak(text=signature).hex()}"


# ---- a landed registration is never lost to a bookkeeping write ----------


class _FullStore:
    """A store whose every write is refused because the database is full."""

    def use(self, tenant_id: str) -> AbstractContextManager[None]:
        return nullcontext()

    def assert_fact(self, *args: object, **kwargs: object) -> None:
        raise MemoryCapReachedError("at the 5 MB free-tier cap")

    def put_reference(self, *args: object, **kwargs: object) -> None:
        raise MemoryCapReachedError("at the 5 MB free-tier cap")


def test_recording_a_registration_into_a_full_database_raises_the_cap_error() -> None:
    with pytest.raises(MemoryCapReachedError):
        record_registration(_FullStore(), 1234, "0xabc", CARD)  # type: ignore[arg-type]


def test_the_record_error_carries_the_hash_and_is_catchable_as_a_registration_error() -> None:
    """The money is already spent. The hash is the only thing it bought."""
    error = RegistrationRecordError("full", tx_hash="0xdeadbeef")

    assert error.tx_hash == "0xdeadbeef"
    assert isinstance(error, RegistrationError)
