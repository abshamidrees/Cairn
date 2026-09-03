"""Tests for the ACP driver and the Evaluator's decision.

The CLI is never actually invoked here: a fake runner records what would have
been run. That keeps the suite offline and makes the important assertion cheap,
which is that every command asks for `--json` rather than parsing a table.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.agent.memory.store import MemoryStore, Observation, counterparty_tenant
from apps.agent.observe.acp import (
    Acp,
    AcpError,
    Deliverable,
    build_deliverable,
    evaluate_deliverable,
)

SUBJECT = "0x00000000000000000000000000000000000000aa"
NOW = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


class FakeRunner:
    """Records invocations and replays canned output."""

    def __init__(self, output: str = "{}") -> None:
        self.calls: list[list[str]] = []
        self.output = output

    def __call__(self, args: Sequence[str]) -> str:
        self.calls.append(list(args))
        return self.output


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MemoryStore]:
    s = MemoryStore.open(tmp_path / "memory.db")
    try:
        yield s
    finally:
        s.close()


# ---- driving the CLI -----------------------------------------------------


def test_every_command_asks_for_json() -> None:
    """Parsing the human-readable tables would break on any CLI restyle."""
    runner = FakeRunner('{"ok":true}')
    acp = Acp(runner=runner)

    acp.whoami()
    acp.jobs()
    acp.history("job-1")
    acp.set_budget("job-1", "0.01")
    acp.complete("job-1", "reason")

    assert runner.calls, "nothing was invoked"
    for call in runner.calls:
        assert call[-1] == "--json", f"{call} did not ask for JSON"


def test_the_chain_id_reaches_the_commands_that_take_one() -> None:
    runner = FakeRunner('{"ok":true}')
    Acp(runner=runner, chain_id=84532).history("job-1")
    assert "--chain-id" in runner.calls[0]
    assert "84532" in runner.calls[0]


def test_job_list_is_not_given_a_chain_flag() -> None:
    """`acp job list` takes no --chain-id, and exits non-zero if given one."""
    runner = FakeRunner("[]")
    Acp(runner=runner, chain_id=84532).jobs()
    assert "--chain-id" not in runner.calls[0]


def test_non_json_output_is_an_error_not_an_empty_result() -> None:
    """The CLI prints prose on some paths. Silently returning {} would hide it."""
    acp = Acp(runner=FakeRunner("Changing a signer's policy requires approval."))
    with pytest.raises(AcpError, match="did not return JSON"):
        acp.whoami()


def test_empty_output_is_tolerated() -> None:
    assert Acp(runner=FakeRunner("   ")).whoami() == {}


def test_the_deliverable_is_sent_as_compact_json() -> None:
    runner = FakeRunner('{"ok":true}')
    deliverable = Deliverable(
        counterparty="cp:base:0xaa",
        standing="grounded",
        confidence=0.84,
        basis=("o1", "o2"),
        methodology="https://docs.usecairn.xyz/methodology",
    )
    Acp(runner=runner).submit("job-1", deliverable)

    call = runner.calls[0]
    payload = call[call.index("--deliverable") + 1]
    assert '"standing":"grounded"' in payload
    assert '"basis":["o1","o2"]' in payload


# ---- what Cairn sells ----------------------------------------------------


def test_the_deliverable_carries_the_observation_ids(store: MemoryStore) -> None:
    with store.use(counterparty_tenant("base", SUBJECT)):
        for client in ("0xa1", "0xb2", "0xc3"):
            store.record_observation(
                Observation(
                    kind="erc8004_feedback",
                    pattern="feedback-untagged",
                    source="base:test",
                    content_hash=f"sha256:{client}",
                    occurred_at=NOW,
                    body={"agent_id": 1, "client": client},
                    reviewer=client,
                )
            )

    deliverable = build_deliverable(store, SUBJECT)

    assert deliverable.standing == "grounded"
    assert len(deliverable.basis) == 3
    assert all(oid for oid in deliverable.basis)
    assert deliverable.confidence is not None


# ---- the Evaluator's decision --------------------------------------------


def test_a_grounded_deliverable_with_a_basis_is_accepted() -> None:
    decision = evaluate_deliverable(
        {"standing": "grounded", "confidence": 0.84, "basis": ["o1", "o2", "o3"]}
    )
    assert decision.accept
    assert "3 observations" in decision.reason


def test_a_grounded_deliverable_with_no_basis_is_refused() -> None:
    """An Evaluator that waves this through is worth nothing."""
    decision = evaluate_deliverable({"standing": "grounded", "confidence": 0.9, "basis": []})
    assert not decision.accept
    assert "no observations" in decision.reason or "must name" in decision.reason


def test_confidence_without_a_basis_is_refused() -> None:
    decision = evaluate_deliverable({"standing": "thin", "confidence": 0.5, "basis": []})
    assert not decision.accept
    assert "confidence" in decision.reason


def test_an_honest_empty_answer_is_accepted() -> None:
    """Thin with no basis and no confidence is the truthful answer, not a failure."""
    decision = evaluate_deliverable({"standing": "thin", "confidence": None, "basis": []})
    assert decision.accept
    assert "no record" in decision.reason


def test_a_suspect_deliverable_must_name_its_contradiction() -> None:
    assert not evaluate_deliverable(
        {"standing": "suspect", "confidence": None, "basis": []}
    ).accept


@pytest.mark.parametrize(
    "payload",
    ["not a dossier", None, 42, [], {"standing": "excellent", "basis": ["o1"]}],
)
def test_anything_that_is_not_a_dossier_is_refused(payload: object) -> None:
    assert not evaluate_deliverable(payload).accept
