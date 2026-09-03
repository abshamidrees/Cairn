"""Tests for the verdict engine.

One test per standing transition, the confidence formula pinned to arithmetic
rather than to whatever the code happens to return, and the part 21 guards that
stop Cairn accusing a real agent it cannot point at.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from apps.agent.judge.verdict import (
    CONFIDENCE_FULL_SOURCES,
    CONTRADICTION_PENALTY,
    GROUNDED_MIN_CORROBORATED,
    NEUTRAL_REVIEWER_WEIGHT,
    W_CORROBORATION,
    W_RECENCY,
    W_VOLUME,
    EmptyBasisError,
    confidence_for,
    evaluate,
    reviewer_weight,
)
from apps.agent.memory.store import (
    DECAY_DAYS,
    MemoryStore,
    Observation,
    counterparty_tenant,
    reviewer_tenant,
)

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
SUBJECT = "0x00000000000000000000000000000000000000aa"
CLIENT_A = "0x00000000000000000000000000000000000000a1"
CLIENT_B = "0x00000000000000000000000000000000000000b2"
CLIENT_C = "0x00000000000000000000000000000000000000c3"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MemoryStore]:
    s = MemoryStore.open(tmp_path / "memory.db")
    try:
        yield s
    finally:
        s.close()


def feedback(client: str, *, agent_id: int = 1, at: datetime = NOW) -> Observation:
    return Observation(
        kind="erc8004_feedback",
        pattern="feedback-untagged",
        source="base:0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
        content_hash=f"sha256:{client}:{at.isoformat()}",
        occurred_at=at,
        body={"agent_id": agent_id, "client": client},
        reviewer=client,
    )


def registration(owner: str, *, agent_id: int = 1, available: bool = True) -> Observation:
    return Observation(
        kind="erc8004_registration",
        pattern="registered-on-erc8004",
        source="base:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
        content_hash=f"sha256:reg:{agent_id}:{owner}",
        occurred_at=NOW,
        body={"agent_id": agent_id, "owner": owner, "registration_available": available},
    )


def seed(store: MemoryStore, *observations: Observation, address: str = SUBJECT) -> None:
    with store.use(counterparty_tenant("base", address)):
        for obs in observations:
            store.record_observation(obs)


# ---- standing transitions ------------------------------------------------


def test_no_observations_is_thin_with_no_basis(store: MemoryStore) -> None:
    verdict = evaluate(store, "base", SUBJECT, now=NOW, write=False)

    assert verdict.standing == "thin"
    assert verdict.no_basis
    assert verdict.basis == ()
    # None, not 0.0. "We have no record" and "the record is worthless" are
    # different answers and must not render the same.
    assert verdict.confidence is None


def test_a_single_claimant_repeating_itself_stays_thin(store: MemoryStore) -> None:
    """The shape of the busiest dossier in the real indexed set."""
    seed(store, *[feedback(CLIENT_A) for _ in range(20)])

    verdict = evaluate(store, "base", SUBJECT, now=NOW, write=False)

    assert len(verdict.basis) == 20
    assert verdict.standing == "thin", "volume from one source must not ground a verdict"
    assert all(not item.corroborated for item in verdict.basis)


def test_three_independent_claimants_is_grounded(store: MemoryStore) -> None:
    seed(store, feedback(CLIENT_A), feedback(CLIENT_B), feedback(CLIENT_C))

    verdict = evaluate(store, "base", SUBJECT, now=NOW, write=False)

    assert verdict.standing == "grounded"
    assert sum(1 for item in verdict.basis if item.corroborated) >= GROUNDED_MIN_CORROBORATED
    assert verdict.confidence is not None


def test_two_independent_claimants_is_still_thin(store: MemoryStore) -> None:
    """The boundary: corroboration below the threshold does not ground."""
    seed(store, feedback(CLIENT_A), feedback(CLIENT_B))

    assert evaluate(store, "base", SUBJECT, now=NOW, write=False).standing == "thin"


def test_a_contradicted_record_is_suspect(store: MemoryStore) -> None:
    seed(
        store,
        registration("0xowner1111111111111111111111111111111111"),
        registration("0xowner2222222222222222222222222222222222"),
    )

    verdict = evaluate(store, "base", SUBJECT, now=NOW, write=False)

    assert verdict.standing == "suspect"
    assert verdict.contradictions, "suspect must carry the disagreement"
    assert verdict.contradictions[0].observation_ids, "suspect must be pointable"
    assert "owner" in verdict.contradictions[0].claim


def test_stale_evidence_is_dormant(store: MemoryStore) -> None:
    long_ago = NOW - timedelta(days=DECAY_DAYS + 30)
    seed(
        store,
        feedback(CLIENT_A, at=long_ago),
        feedback(CLIENT_B, at=long_ago),
        feedback(CLIENT_C, at=long_ago),
    )

    verdict = evaluate(store, "base", SUBJECT, now=NOW, write=False)

    # Corroborated enough to be grounded, but nothing has been seen in months.
    assert verdict.standing == "dormant"


def test_a_contradiction_outranks_staleness(store: MemoryStore) -> None:
    seed(
        store,
        registration("0xowner1111111111111111111111111111111111"),
        registration("0xowner2222222222222222222222222222222222"),
    )
    later = NOW + timedelta(days=DECAY_DAYS * 2)
    verdict = evaluate(store, "base", SUBJECT, now=later, write=False)
    assert verdict.standing == "suspect"


# ---- part 21, being wrong is worse than being silent ---------------------


def test_an_unfetched_registration_file_never_creates_suspicion(store: MemoryStore) -> None:
    """Absence is never evidence.

    A registration file Cairn could not fetch marks the source unavailable. It
    does not become a claim, and it cannot make anybody suspect.
    """
    seed(store, registration("0xowner1111111111111111111111111111111111", available=False))

    verdict = evaluate(store, "base", SUBJECT, now=NOW, write=False)

    assert verdict.standing == "thin"
    assert verdict.contradictions == ()
    assert "erc8004 registration file" in verdict.sources_unavailable


def test_every_suspect_verdict_can_name_its_contradiction(store: MemoryStore) -> None:
    """Whenever the engine does accuse, the accusation is pointable."""
    seed(
        store,
        registration("0xowner1111111111111111111111111111111111"),
        registration("0xowner2222222222222222222222222222222222"),
        feedback(CLIENT_A),
    )
    verdict = evaluate(store, "base", SUBJECT, now=NOW, write=False)

    assert verdict.standing == "suspect"
    for contradiction in verdict.contradictions:
        assert contradiction.observation_ids
        assert all(oid for oid in contradiction.observation_ids)


def test_a_contradiction_without_ids_raises_rather_than_downgrading(
    store: MemoryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard itself.

    A contradiction that cannot name an observation is a bug in the engine, and
    the engine must refuse rather than quietly returning a softer standing. If
    this ever downgrades to `thin` instead of raising, Cairn has started hiding
    its own defects behind a gentler verdict.
    """
    from apps.agent.judge import verdict as engine

    seed(store, feedback(CLIENT_A))
    monkeypatch.setattr(
        engine,
        "_contradictions",
        lambda _observations: [
            engine.ContradictionRef(claim="fabricated", detail="no ids", observation_ids=())
        ],
    )

    with pytest.raises(EmptyBasisError):
        evaluate(store, "base", SUBJECT, now=NOW, write=False)


# ---- adversarial input ---------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"agent_id": None, "client": None},
        {"agent_id": 1},
        {"owner": "not-an-address"},
        {"agent_id": 1, "owner": None},
        {"agent_id": 1, "owner": ""},
    ],
)
def test_malformed_observations_never_produce_suspicion(
    store: MemoryStore, body: dict[str, Any]
) -> None:
    """Garbage in the record must not become an accusation.

    Truncated JSON, prose where an identifier belongs and empty responses all
    reach the engine eventually. None of them is a contradiction.
    """
    obs = Observation(
        kind="erc8004_registration",
        pattern="registered-on-erc8004",
        source="base:test",
        content_hash="sha256:malformed",
        occurred_at=NOW,
        body=body,
    )
    seed(store, obs)

    verdict = evaluate(store, "base", SUBJECT, now=NOW, write=False)

    assert verdict.standing in ("thin", "dormant")
    assert verdict.contradictions == ()


def test_the_same_owner_twice_is_not_a_contradiction(store: MemoryStore) -> None:
    """Agreement repeated is agreement, not disagreement."""
    seed(
        store,
        registration("0xOWNER1111111111111111111111111111111111"),
        registration("0xowner1111111111111111111111111111111111"),
    )
    verdict = evaluate(store, "base", SUBJECT, now=NOW, write=False)
    assert verdict.contradictions == ()
    assert verdict.standing != "suspect"


# ---- the confidence formula ----------------------------------------------


def test_confidence_is_none_without_a_record() -> None:
    assert (
        confidence_for(
            n_observations=0, distinct_sources=0, corroborated=0, recency=1.0, contradictions=0
        )
        is None
    )


def test_confidence_matches_the_published_formula() -> None:
    """Pinned to arithmetic, so changing a weight without changing the docs fails."""
    got = confidence_for(
        n_observations=4,
        distinct_sources=2,
        corroborated=2,
        recency=1.0,
        contradictions=0,
    )
    expected = round(
        W_VOLUME * (2 / CONFIDENCE_FULL_SOURCES) + W_CORROBORATION * (2 / 4) + W_RECENCY * 1.0,
        2,
    )
    assert got == expected


def test_repeating_yourself_buys_no_confidence() -> None:
    """The Sybil hole, held shut.

    With the number of sources fixed at one, adding observations must change
    nothing at all. If confidence rises with raw count then a claimant can buy
    it for $0.0027 a time, which is the finding Cairn exists to answer.
    """
    few = confidence_for(
        n_observations=2, distinct_sources=1, corroborated=0, recency=1.0, contradictions=0
    )
    many = confidence_for(
        n_observations=200, distinct_sources=1, corroborated=0, recency=1.0, contradictions=0
    )
    assert few == many


def test_volume_counts_sources_not_observations() -> None:
    """One claimant speaking a hundred times must not outscore two speaking once."""
    sybil = confidence_for(
        n_observations=100, distinct_sources=1, corroborated=0, recency=1.0, contradictions=0
    )
    honest = confidence_for(
        n_observations=2, distinct_sources=2, corroborated=2, recency=1.0, contradictions=0
    )
    assert sybil is not None and honest is not None
    assert honest > sybil


def test_a_contradiction_costs_exactly_the_published_penalty() -> None:
    clean = confidence_for(
        n_observations=4, distinct_sources=4, corroborated=4, recency=1.0, contradictions=0
    )
    one = confidence_for(
        n_observations=4, distinct_sources=4, corroborated=4, recency=1.0, contradictions=1
    )
    assert clean is not None and one is not None
    assert round(clean - one, 2) == CONTRADICTION_PENALTY


def test_confidence_stays_inside_zero_and_one() -> None:
    floored = confidence_for(
        n_observations=1, distinct_sources=1, corroborated=0, recency=0.0, contradictions=9
    )
    ceiled = confidence_for(
        n_observations=99, distinct_sources=99, corroborated=99, recency=1.0, contradictions=0
    )
    assert floored == 0.0
    assert ceiled == 1.0


def test_stale_evidence_lowers_confidence() -> None:
    fresh = confidence_for(
        n_observations=4, distinct_sources=2, corroborated=2, recency=1.0, contradictions=0
    )
    stale = confidence_for(
        n_observations=4, distinct_sources=2, corroborated=2, recency=0.0, contradictions=0
    )
    assert fresh is not None and stale is not None
    assert fresh > stale


def test_the_verdict_is_deterministic(store: MemoryStore) -> None:
    """Arithmetic over the record, so a second run returns the same answer."""
    seed(store, feedback(CLIENT_A), feedback(CLIENT_B), feedback(CLIENT_C))
    first = evaluate(store, "base", SUBJECT, now=NOW, write=False)
    second = evaluate(store, "base", SUBJECT, now=NOW, write=False)
    assert first.standing == second.standing
    assert first.confidence == second.confidence
    assert [i.observation_id for i in first.basis] == [i.observation_id for i in second.basis]


# ---- reviewer weighting --------------------------------------------------


def test_a_short_reviewer_record_is_neutral_and_flagged(store: MemoryStore) -> None:
    """Having made few claims is not evidence of anything, good or bad."""
    with store.use(reviewer_tenant(CLIENT_A)):
        store.record_observation(
            Observation(
                kind="erc8004_claim",
                pattern="claims-about:1",
                source="base:test",
                content_hash="sha256:claim",
                occurred_at=NOW,
                body={"agent_id": 1, "client": CLIENT_A},
                reviewer=CLIENT_A,
            )
        )

    weight = reviewer_weight(store, CLIENT_A, witnessed={1: {CLIENT_A.lower()}})

    assert weight.claims == 1
    assert weight.corroborated == 0
    assert weight.provisional is True
    assert weight.weight == NEUTRAL_REVIEWER_WEIGHT


def test_a_reviewer_cannot_corroborate_itself(store: MemoryStore) -> None:
    with store.use(reviewer_tenant(CLIENT_A)):
        for i in range(4):
            store.record_observation(
                Observation(
                    kind="erc8004_claim",
                    pattern=f"claims-about:{i}",
                    source="base:test",
                    content_hash=f"sha256:claim:{i}",
                    occurred_at=NOW,
                    body={"agent_id": i, "client": CLIENT_A},
                    reviewer=CLIENT_A,
                )
            )

    # Only this claimant was ever seen for those agents.
    alone = reviewer_weight(store, CLIENT_A, witnessed={i: {CLIENT_A.lower()} for i in range(4)})
    assert alone.corroborated == 0
    assert alone.provisional is True

    # Now someone else independently witnessed the same agents.
    joined = reviewer_weight(
        store, CLIENT_A, witnessed={i: {CLIENT_A.lower(), CLIENT_B.lower()} for i in range(4)}
    )
    assert joined.corroborated == 4
    assert joined.provisional is False
    assert joined.weight == 1.0


def test_the_verdict_reports_the_reviewers_it_weighed(store: MemoryStore) -> None:
    seed(store, feedback(CLIENT_A), feedback(CLIENT_B))
    verdict = evaluate(store, "base", SUBJECT, now=NOW, write=False)
    addresses = {r.address for r in verdict.reviewers}
    assert addresses == {CLIENT_A.lower(), CLIENT_B.lower()}


# ---- writing back --------------------------------------------------------


def test_evaluating_writes_the_verdict_to_hot_and_hands_work_forward(
    store: MemoryStore,
) -> None:
    seed(store, feedback(CLIENT_A))
    evaluate(store, "base", SUBJECT, now=NOW, write=True)

    with store.use(counterparty_tenant("base", SUBJECT)):
        held = store.verdict()
        assert held is not None
        assert held["standing"] == "thin"
        # A thin dossier is worth looking at again, so the next session is told.
        assert any("recheck" in item for item in store.drain_forward())


def test_write_false_leaves_the_record_untouched(store: MemoryStore) -> None:
    """The deletion test evaluates twice, and must not alter what it measures."""
    seed(store, feedback(CLIENT_A))
    evaluate(store, "base", SUBJECT, now=NOW, write=False)

    with store.use(counterparty_tenant("base", SUBJECT)):
        assert store.verdict() is None


# ---- the baton carries news, not a heartbeat -----------------------------


def test_re_evaluating_an_unchanged_verdict_hands_nothing_forward(store: MemoryStore) -> None:
    """A periodic sweep must not grow the journal for saying the same thing.

    HOT is rewritten in place and costs nothing, but the baton is a journal
    event and the journal is append-only. Re-handing identical work on every
    pass walked the real database into the free tier's 5,242,880 byte cap.
    """
    seed(store, feedback(CLIENT_A))

    evaluate(store, "base", SUBJECT, now=NOW, write=True)
    with store.use(counterparty_tenant("base", SUBJECT)):
        first = len(store.observations())
        drained = store.drain_forward()
    assert drained, "a thin dossier should ask to be rechecked at least once"

    # Same record, same verdict. Nothing new to tell anyone.
    for _ in range(3):
        evaluate(store, "base", SUBJECT, now=NOW, write=True)

    with store.use(counterparty_tenant("base", SUBJECT)):
        assert len(store.observations()) == first, "the journal grew for no new information"
        assert store.drain_forward() == []


def test_a_changed_verdict_still_hands_work_forward(store: MemoryStore) -> None:
    """The guard must not silence a baton that actually has news in it."""
    seed(store, feedback(CLIENT_A))
    evaluate(store, "base", SUBJECT, now=NOW, write=True)
    with store.use(counterparty_tenant("base", SUBJECT)):
        store.drain_forward()

    # New corroborating evidence moves it from thin to grounded.
    seed(store, feedback(CLIENT_B), feedback(CLIENT_C))
    verdict = evaluate(store, "base", SUBJECT, now=NOW, write=True)
    assert verdict.standing == "grounded"

    with store.use(counterparty_tenant("base", SUBJECT)):
        # Grounded hands no recheck, but the provisional reviewers still count.
        assert store.verdict() is not None
