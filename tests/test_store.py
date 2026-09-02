"""Tests for the memory adapter.

These assert the four behaviours the tier policy actually rests on: dossiers are
isolated, a third occurrence promotes, a contradiction overwrites and stays
auditable, and aged evidence retires with a reason. Each one is written so that
removing the corresponding logic from store.py makes it fail.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from apps.agent.memory.store import (
    BEHAVIOUR,
    DECAY_DAYS,
    PROMOTION_THRESHOLD,
    Archived,
    MemoryStore,
    NullStore,
    Observation,
    counterparty_tenant,
    reviewer_tenant,
)

BASE = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

ALICE = counterparty_tenant("base", "0x00000000000000000000000000000000000000AA")
BOB = counterparty_tenant("base", "0x00000000000000000000000000000000000000bb")


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MemoryStore]:
    s = MemoryStore.open(tmp_path / "memory.db")
    try:
        yield s
    finally:
        # SQLite holds the file open, and Windows will not delete a locked file.
        s.close()


def observation(
    pattern: str = "settles-escrow-on-time",
    *,
    at: datetime = BASE,
    kind: str = "escrow_settled",
    body: dict[str, object] | None = None,
) -> Observation:
    return Observation(
        kind=kind,
        pattern=pattern,
        source="base:0x238E541BfefD82238730D00a2208E5497F1832E0",
        content_hash=f"sha256:{pattern}:{at.isoformat()}",
        occurred_at=at,
        body=body or {"job": "0x1"},
    )


def journal_kinds(store: MemoryStore) -> list[str]:
    """The `acted` side of every event, which is where tier migrations show up."""
    kinds: list[str] = []
    for event in store._m.read_events(limit=1000):
        acted = event.get("acted")
        if isinstance(acted, dict):
            kinds.append(str(acted.get("tier")))
    return kinds


# ---- tenancy -------------------------------------------------------------


def test_two_tenants_cannot_see_each_others_rows(store: MemoryStore) -> None:
    with store.use(ALICE):
        store.record_observation(observation())
        store.assert_fact("identity", "operator", "alice-labs", observation_id="o1")
        store.put_verdict({"standing": "grounded"})

    with store.use(BOB):
        assert store.observations() == []
        assert store.facts() == []
        assert store.fact("identity", "operator") is None
        assert store.verdict() is None

    # Alice is untouched by Bob having looked.
    with store.use(ALICE):
        assert len(store.observations()) == 1
        assert store.fact("identity", "operator") is not None


def test_a_reviewer_dossier_is_a_separate_tenant_from_a_counterparty(
    store: MemoryStore,
) -> None:
    reviewer = reviewer_tenant("0x00000000000000000000000000000000000000AA")
    assert reviewer != ALICE

    with store.use(ALICE):
        store.assert_fact("identity", "operator", "alice-labs", observation_id="o1")
    with store.use(reviewer):
        assert store.fact("identity", "operator") is None


def test_use_restores_the_previous_tenant(store: MemoryStore) -> None:
    with store.use(ALICE):
        with store.use(BOB):
            store.record_observation(observation())
        # Back in Alice's dossier, which never saw that observation.
        assert store.observations() == []


# ---- promotion -----------------------------------------------------------


def test_third_occurrence_promotes_the_pattern_to_a_warm_entity(store: MemoryStore) -> None:
    with store.use(ALICE):
        for i in range(PROMOTION_THRESHOLD - 1):
            written = store.record_observation(observation(at=BASE + timedelta(days=i)))
            assert written.promotion is None, "promoted before the threshold"
        assert store.fact(BEHAVIOUR, "settles-escrow-on-time") is None

        written = store.record_observation(observation(at=BASE + timedelta(days=2)))

        assert written.promotion is not None
        assert written.promotion.n == PROMOTION_THRESHOLD
        assert len(written.promotion.observation_ids) == PROMOTION_THRESHOLD

        entity = store.fact(BEHAVIOUR, "settles-escrow-on-time")
        assert entity is not None
        assert entity["body"]["n"] == PROMOTION_THRESHOLD
        assert entity["body"]["first_seen"] < entity["body"]["last_seen"]


def test_promotion_is_itself_recorded_in_the_journal(store: MemoryStore) -> None:
    with store.use(ALICE):
        for i in range(PROMOTION_THRESHOLD):
            store.record_observation(observation(at=BASE + timedelta(days=i)))

        assert "WARM" in journal_kinds(store), "the tier migration was not journalled"

        # A fourth occurrence updates the count without re-announcing the promotion.
        store.record_observation(observation(at=BASE + timedelta(days=3)))
        assert journal_kinds(store).count("WARM") == 1

        entity = store.fact(BEHAVIOUR, "settles-escrow-on-time")
        assert entity is not None
        assert entity["body"]["n"] == PROMOTION_THRESHOLD + 1


def test_occurrences_outside_the_decay_window_do_not_promote(store: MemoryStore) -> None:
    spread = timedelta(days=DECAY_DAYS * 2)
    with store.use(ALICE):
        for i in range(PROMOTION_THRESHOLD):
            written = store.record_observation(observation(at=BASE + spread * i))
        # Three occurrences, but no three of them sit inside one window.
        assert written.promotion is None
        assert store.fact(BEHAVIOUR, "settles-escrow-on-time") is None


def test_distinct_patterns_are_counted_separately(store: MemoryStore) -> None:
    with store.use(ALICE):
        for i in range(PROMOTION_THRESHOLD):
            when = BASE + timedelta(days=i)
            store.record_observation(observation("rejects-on-delivery", at=when))
            store.record_observation(observation("settles-escrow-on-time", at=when))
        assert store.fact(BEHAVIOUR, "rejects-on-delivery") is not None
        assert store.fact(BEHAVIOUR, "settles-escrow-on-time") is not None

    with store.use(ALICE):
        only_one = store.observations(pattern="rejects-on-delivery")
        assert len(only_one) == PROMOTION_THRESHOLD


# ---- contradiction -------------------------------------------------------


def test_contradicting_write_overwrites_the_entity_and_journals_both_values(
    store: MemoryStore,
) -> None:
    with store.use(ALICE):
        assert store.assert_fact("identity", "operator", "alice-labs", observation_id="o1") is None

        contradiction = store.assert_fact(
            "identity", "operator", "someone-else", observation_id="o2"
        )

        assert contradiction is not None
        assert contradiction.old == "alice-labs"
        assert contradiction.new == "someone-else"
        assert contradiction.observation_id == "o2"

        # Overwritten, not duplicated: the entity cannot drift.
        rows = [e for e in store.facts("identity") if e["name"] == "operator"]
        assert len(rows) == 1
        assert rows[0]["body"]["value"] == "someone-else"

        # Both values survive in the journal, so the change stays auditable.
        journalled = [
            event["evaluated"]["contradiction"]
            for event in store._m.read_events(limit=100)
            if isinstance(event.get("evaluated"), dict)
            and "contradiction" in event["evaluated"]
        ]
        assert len(journalled) == 1
        assert journalled[0]["old"] == "alice-labs"
        assert journalled[0]["new"] == "someone-else"


def test_rewriting_the_same_value_is_not_a_contradiction(store: MemoryStore) -> None:
    with store.use(ALICE):
        store.assert_fact("identity", "operator", "alice-labs", observation_id="o1")
        assert store.assert_fact("identity", "operator", "alice-labs", observation_id="o2") is None


# ---- demotion ------------------------------------------------------------


def test_an_aged_entity_archives_with_a_reason(store: MemoryStore) -> None:
    long_ago = BASE - timedelta(days=DECAY_DAYS * 2)
    with store.use(ALICE):
        for i in range(PROMOTION_THRESHOLD):
            store.record_observation(observation(at=long_ago + timedelta(days=i)))
        assert store.fact(BEHAVIOUR, "settles-escrow-on-time") is not None

        retired = store.archive_stale(now=BASE)

        assert retired == [
            Archived(
                category=BEHAVIOUR,
                name="settles-escrow-on-time",
                reason="evidence aged out",
                last_seen=retired[0].last_seen,
            )
        ]
        assert retired[0].reason == "evidence aged out"

        # Archived, not deleted, and gone from the entity table either way.
        assert store.fact(BEHAVIOUR, "settles-escrow-on-time") is None
        assert store.facts(BEHAVIOUR) == []

        # The client cannot read an archived row back, so the reason and the
        # retired body have to be in the journal or they are lost.
        archivals = [
            event["evaluated"]["archival"]
            for event in store._m.read_events(limit=100)
            if isinstance(event.get("evaluated"), dict) and "archival" in event["evaluated"]
        ]
        assert len(archivals) == 1
        assert archivals[0]["name"] == "settles-escrow-on-time"
        assert archivals[0]["body"]["n"] == PROMOTION_THRESHOLD
        assert "ARCHIVE" in journal_kinds(store)


def test_a_fact_still_inside_the_window_is_not_archived(store: MemoryStore) -> None:
    with store.use(ALICE):
        for i in range(PROMOTION_THRESHOLD):
            store.record_observation(observation(at=BASE + timedelta(days=i)))

        assert store.archive_stale(now=BASE + timedelta(days=DECAY_DAYS - 1)) == []
        assert store.fact(BEHAVIOUR, "settles-escrow-on-time") is not None


def test_archiving_one_dossier_leaves_another_untouched(store: MemoryStore) -> None:
    long_ago = BASE - timedelta(days=DECAY_DAYS * 2)
    for tenant in (ALICE, BOB):
        with store.use(tenant):
            for i in range(PROMOTION_THRESHOLD):
                store.record_observation(observation(at=long_ago + timedelta(days=i)))

    with store.use(ALICE):
        assert len(store.archive_stale(now=BASE)) == 1
    with store.use(BOB):
        assert store.fact(BEHAVIOUR, "settles-escrow-on-time") is not None


# ---- the session baton ---------------------------------------------------


def test_forward_is_drained_once_across_sessions(store: MemoryStore) -> None:
    with store.use(ALICE):
        store.hand_forward([{"recheck": ALICE}, {"corroborate": "claim-7"}])

        first = store.drain_forward()
        assert {"recheck": ALICE} in first
        assert {"corroborate": "claim-7"} in first

        # A second boot must not pick the same work up again.
        assert store.drain_forward() == []


def test_a_contradiction_hands_corroboration_forward(store: MemoryStore) -> None:
    with store.use(ALICE):
        store.drain_forward()  # start from a clean cursor
        store.assert_fact("identity", "operator", "alice-labs", observation_id="o1")
        store.assert_fact("identity", "operator", "someone-else", observation_id="o2")

        assert {"corroborate": "operator"} in store.drain_forward()


def test_the_baton_is_per_dossier(store: MemoryStore) -> None:
    with store.use(ALICE):
        store.hand_forward([{"recheck": ALICE}])
    with store.use(BOB):
        assert store.drain_forward() == []


# ---- the other tiers -----------------------------------------------------


def test_hot_verdict_is_rewritten_in_place(store: MemoryStore) -> None:
    with store.use(ALICE):
        store.put_verdict({"standing": "thin", "confidence": None})
        store.put_verdict({"standing": "grounded", "confidence": 0.87})

        current = store.verdict()
        assert current is not None
        assert current["standing"] == "grounded"


def test_reference_round_trips_to_the_same_mapping(store: MemoryStore) -> None:
    with store.use(ALICE):
        store.put_reference("scoring-policy", {"version": "0.1.0", "threshold": 3})
        # get_reference hands the body back as a JSON string, so asserting the
        # value rather than merely that something came back is the point here.
        assert store.reference("scoring-policy") == {"version": "0.1.0", "threshold": 3}
        assert store.reference("never-written") is None


# ---- the deletion boundary -----------------------------------------------


def test_null_store_reads_empty_and_writes_nothing() -> None:
    """The deletion test's other half. Every read empty, every write a no-op."""
    null = NullStore()
    with null.use(ALICE):
        written = null.record_observation(observation())
        assert written.promotion is None

        null.put_verdict({"standing": "grounded"})
        null.assert_fact("identity", "operator", "alice-labs", observation_id="o1")
        null.hand_forward([{"recheck": ALICE}])

        assert null.observations() == []
        assert null.facts() == []
        assert null.fact(BEHAVIOUR, "settles-escrow-on-time") is None
        assert null.verdict() is None
        assert null.drain_forward() == []
        assert null.archive_stale() == []
