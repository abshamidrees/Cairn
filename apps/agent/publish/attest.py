"""Publish a verdict on Base, so the record survives outside Cairn.

ERC-8004 defers verification to a Validation Registry with no mainnet
deployment, so there is nowhere on Base to write a grounded verdict into. This
publishes into `packages/chain/contracts/CairnAttestations.sol` instead, which
is small enough to read in a minute and stores nothing it cannot evidence.

The reputation registry's own write path was considered and rejected. Its
implementation is unverified, and the selector observed on the wire
(`0x3c036a7e`) does not match any signature we could reconstruct. Calling an
unverified contract with a guessed signature, using someone's ETH, to publish a
judgment about a real third party, is the failure mode part 21 exists to
prevent. If the ABI is published later this becomes a two-line change.

Encoding is separated from sending on purpose: `encode` is pure and tested, and
nothing in this module signs anything unless a caller passes a key in.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from web3 import Web3

from apps.agent.judge.verdict import Verdict
from apps.agent.memory.store import Store, counterparty_tenant

CONTRACT = Path(__file__).resolve().parent.parent.parent.parent / (
    "packages/chain/contracts/CairnAttestations.sol"
)
SOLC_VERSION = "0.8.24"
BASE_CHAIN_ID = 8453

#: Basis points, so a confidence of 0.84 publishes as 8400 and nothing is lost
#: to float representation on chain.
BPS = 10_000


class AttestationError(RuntimeError):
    """The attestation could not be published, or would have been meaningless."""


@dataclass(frozen=True)
class AttestationCall:
    """Exactly what goes on chain. Pure data, so it can be checked offline."""

    counterparty: str
    standing: bytes
    confidence_bps: int
    basis_count: int
    basis_hash: bytes
    evaluated_at: int

    def as_args(self) -> tuple[str, bytes, int, int, bytes, int]:
        return (
            self.counterparty,
            self.standing,
            self.confidence_bps,
            self.basis_count,
            self.basis_hash,
            self.evaluated_at,
        )

    def as_payload(self) -> dict[str, Any]:
        return {
            "counterparty": self.counterparty,
            "standing": self.standing.hex(),
            "confidence_bps": self.confidence_bps,
            "basis_count": self.basis_count,
            "basis_hash": self.basis_hash.hex(),
            "evaluated_at": self.evaluated_at,
        }


def _address_of(tenant: str) -> str:
    """cp:base:0xabc -> checksummed 0xabc"""
    return Web3.to_checksum_address(tenant.split(":")[-1])


def basis_hash(observation_ids: tuple[str, ...]) -> bytes:
    """keccak over the observation ids, in the order the verdict used them.

    A reader holding the dossier can recompute this and prove the published
    verdict is the one Cairn actually held. Sorting is deliberate: the hash must
    not depend on the order rows came back from the database.
    """
    joined = "\n".join(sorted(observation_ids))
    return bytes(Web3.keccak(text=joined))


def encode(verdict: Verdict) -> AttestationCall:
    """Turn a verdict into the call that publishes it.

    Refuses the same thing the contract refuses, one layer earlier: a grounded
    verdict with nothing behind it is not publishable, because publishing it
    would put an unevidenced claim about a named third party on a public chain
    where it cannot be taken back.
    """
    ids = tuple(item.observation_id for item in verdict.basis)
    if verdict.standing == "grounded" and not ids:
        raise AttestationError("refusing to publish a grounded verdict with an empty basis")
    if verdict.standing == "suspect" and not any(
        c.observation_ids for c in verdict.contradictions
    ):
        raise AttestationError("refusing to publish a suspect verdict with no contradiction")

    confidence_bps = 0 if verdict.confidence is None else round(verdict.confidence * BPS)
    if not 0 <= confidence_bps <= BPS:
        raise AttestationError(f"confidence {verdict.confidence} is outside 0 to 1")

    evaluated = verdict.evaluated_at
    stamp = int(
        __import__("datetime").datetime.fromisoformat(evaluated.replace("Z", "+00:00")).timestamp()
    )

    return AttestationCall(
        counterparty=_address_of(verdict.counterparty),
        standing=bytes(Web3.keccak(text=verdict.standing)),
        confidence_bps=confidence_bps,
        basis_count=len(ids),
        basis_hash=basis_hash(ids),
        evaluated_at=stamp,
    )


def compile_contract() -> dict[str, Any]:
    """Compile the attestation contract. Requires solc, installed on demand."""
    import solcx

    try:
        solcx.set_solc_version(SOLC_VERSION)
    except Exception:
        solcx.install_solc(SOLC_VERSION)
        solcx.set_solc_version(SOLC_VERSION)

    compiled = solcx.compile_files(
        [str(CONTRACT)], output_values=["abi", "bin"], optimize=True
    )
    key = next(k for k in compiled if "CairnAttestations" in k)
    return {"abi": compiled[key]["abi"], "bytecode": compiled[key]["bin"]}


class Attestor:
    """Signs and sends. Everything it needs is passed in, nothing is ambient."""

    def __init__(self, w3: Web3, private_key: str, contract_address: str | None = None) -> None:
        if not private_key:
            raise AttestationError("no attestor key: set CAIRN_ATTESTOR_KEY")
        self._w3 = w3
        self._account = w3.eth.account.from_key(private_key)
        self._artifact = compile_contract()
        self._address = (
            Web3.to_checksum_address(contract_address) if contract_address else None
        )

    @property
    def address(self) -> str:
        return str(self._account.address)

    def deploy(self) -> tuple[str, str]:
        """Deploy the attestation contract. Returns (tx hash, contract address)."""
        contract = self._w3.eth.contract(
            abi=self._artifact["abi"], bytecode=self._artifact["bytecode"]
        )
        tx = contract.constructor().build_transaction(
            {
                "from": self._account.address,
                "nonce": self._w3.eth.get_transaction_count(self._account.address),
                "chainId": BASE_CHAIN_ID,
            }
        )
        signed = self._account.sign_transaction(tx)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        created = receipt.get("contractAddress")
        if created is None:
            raise AttestationError("the deployment receipt carried no contract address")
        self._address = Web3.to_checksum_address(created)
        return tx_hash.hex(), self._address

    def publish(self, verdict: Verdict, *, store: Store | None = None) -> str:
        """Publish one verdict and return the transaction hash.

        When a store is passed, the transaction is recorded in the
        counterparty's own dossier, so the explorer can show what was published
        about an agent alongside the observations it was derived from.
        """
        if self._address is None:
            raise AttestationError("no contract address: deploy first, or pass one in")

        call = encode(verdict)
        contract = self._w3.eth.contract(address=self._address, abi=self._artifact["abi"])
        tx = contract.functions.attest(*call.as_args()).build_transaction(
            {
                "from": self._account.address,
                "nonce": self._w3.eth.get_transaction_count(self._account.address),
                "chainId": BASE_CHAIN_ID,
            }
        )
        signed = self._account.sign_transaction(tx)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        published = tx_hash.hex()

        if store is not None:
            record_attestation(store, verdict, published, self._address)
        return published


def record_attestation(
    store: Store, verdict: Verdict, tx_hash: str, contract_address: str
) -> None:
    """Note in the dossier that this verdict was published, and where.

    An attestation is a fact about the counterparty, so it lives in memory with
    everything else rather than in a side table the verdict cannot see.
    """
    tenant = verdict.counterparty
    if not tenant.startswith("cp:"):
        tenant = counterparty_tenant("base", verdict.counterparty)
    with store.use(tenant):
        store.assert_fact(
            "attestation",
            "latest",
            f"0x{tx_hash.removeprefix('0x')}",
            observation_id=tx_hash,
        )
        store.put_reference(
            "attestation-contract",
            {"address": contract_address, "chain_id": BASE_CHAIN_ID},
        )


def attestor_from_env(rpc_url: str | None = None) -> Attestor:
    """Build an Attestor from the environment. The key is never logged."""
    url = rpc_url or os.environ.get("BASE_RPC_URL") or "https://mainnet.base.org"
    key = os.environ.get("CAIRN_ATTESTOR_KEY", "")
    contract = os.environ.get("CAIRN_ATTESTATION_CONTRACT") or None
    return Attestor(Web3(Web3.HTTPProvider(url)), key, contract)


def artifact_json() -> str:
    """The compiled ABI, for anyone who wants to read the events themselves."""
    return json.dumps(compile_contract()["abi"], indent=2)
