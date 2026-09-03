"""Tests for the attestation encoding.

Nothing here touches a chain or a key. `encode` is pure, which is the point of
separating it: what goes on Base is checkable offline, before anyone spends gas
publishing a judgment about a real third party that cannot be taken back.
"""

from __future__ import annotations

import pytest
from eth_utils import keccak

from apps.agent.judge.verdict import BasisItem, ContradictionRef, Verdict
from apps.agent.publish.attest import (
    BPS,
    AttestationError,
    basis_hash,
    compile_contract,
    encode,
)

EVALUATED = "2026-09-01T12:00:00.000Z"
TENANT = "cp:base:0x00000000000000000000000000000000000000aa"


def item(observation_id: str) -> BasisItem:
    return BasisItem(
        observation_id=observation_id,
        kind="erc8004_feedback",
        occurred_at=EVALUATED,
        content_hash=f"sha256:{observation_id}",
        source="base:test",
        reviewer=None,
        corroborated=True,
        weight=1.0,
    )


def verdict(
    standing: str = "grounded",
    *,
    confidence: float | None = 0.84,
    ids: tuple[str, ...] = ("o1", "o2", "o3"),
    contradictions: tuple[ContradictionRef, ...] = (),
) -> Verdict:
    return Verdict(
        counterparty=TENANT,
        standing=standing,  # type: ignore[arg-type]
        confidence=confidence,
        basis=tuple(item(i) for i in ids),
        contradictions=contradictions,
        evaluated_at=EVALUATED,
    )


# ---- the basis hash ------------------------------------------------------


def test_the_basis_hash_does_not_depend_on_row_order() -> None:
    """The database may return rows in any order. The published hash may not."""
    assert basis_hash(("o1", "o2", "o3")) == basis_hash(("o3", "o1", "o2"))


def test_a_different_basis_hashes_differently() -> None:
    assert basis_hash(("o1", "o2")) != basis_hash(("o1", "o2", "o3"))


def test_the_hash_is_reproducible_by_a_reader_holding_the_dossier() -> None:
    """Anyone with the observation ids can check what was published."""
    assert basis_hash(("b", "a")) == keccak(text="a\nb")


# ---- encoding ------------------------------------------------------------


def test_confidence_publishes_as_basis_points() -> None:
    """Floats do not survive a chain intact, so 0.84 goes on as 8400."""
    assert encode(verdict(confidence=0.84)).confidence_bps == 8400
    assert encode(verdict(confidence=1.0)).confidence_bps == BPS


def test_a_thin_verdict_with_no_confidence_publishes_zero() -> None:
    call = encode(verdict("thin", confidence=None, ids=()))
    assert call.confidence_bps == 0
    assert call.basis_count == 0


def test_the_standing_is_published_as_its_hash() -> None:
    assert encode(verdict("thin", confidence=None, ids=())).standing == keccak(text="thin")


def test_the_counterparty_is_checksummed_from_the_tenant() -> None:
    call = encode(verdict())
    assert call.counterparty.startswith("0x")
    assert call.counterparty != call.counterparty.lower(), "address was not checksummed"


def test_the_basis_count_matches_the_observations_used() -> None:
    assert encode(verdict(ids=("o1", "o2", "o3", "o4"))).basis_count == 4


# ---- what will not be published ------------------------------------------


def test_a_grounded_verdict_with_an_empty_basis_is_refused() -> None:
    """Publishing this would put an unevidenced claim about a named agent on a
    public chain, where it cannot be taken back."""
    with pytest.raises(AttestationError, match="empty basis"):
        encode(verdict("grounded", ids=()))


def test_a_suspect_verdict_with_no_contradiction_is_refused() -> None:
    with pytest.raises(AttestationError, match="no contradiction"):
        encode(verdict("suspect", confidence=None, ids=("o1",)))


def test_a_suspect_verdict_that_names_its_contradiction_is_publishable() -> None:
    call = encode(
        verdict(
            "suspect",
            confidence=0.3,
            ids=("o1", "o2"),
            contradictions=(
                ContradictionRef(
                    claim="agent 1 owner",
                    detail="two owners",
                    observation_ids=("o1", "o2"),
                ),
            ),
        )
    )
    assert call.standing == keccak(text="suspect")
    assert call.basis_count == 2


# ---- the contract itself -------------------------------------------------


def test_the_contract_compiles_and_exposes_attest() -> None:
    artifact = compile_contract()
    names = [entry.get("name") for entry in artifact["abi"]]
    assert "attest" in names
    assert "Attested" in names
    assert artifact["bytecode"].startswith("0x") or artifact["bytecode"]


def test_the_contract_refuses_the_same_thing_the_encoder_does() -> None:
    """The rule is enforced twice: once off chain, once where it is permanent."""
    from apps.agent.publish.attest import CONTRACT

    text = CONTRACT.read_text(encoding="utf-8")
    assert "EmptyBasisForGroundedVerdict" in text
    assert 'keccak256("grounded")' in text
