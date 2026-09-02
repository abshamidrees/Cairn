"""Tests for the deletion test, which is the gate the whole submission rests on.

The script is CI's tripwire: it must exit non-zero the day Cairn starts
answering without reading its record. A tripwire nothing tests is a tripwire
nobody knows is disconnected.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

from apps.agent.judge.verdict import Verdict
from apps.agent.memory.store import MemoryStore, NullStore, Observation, counterparty_tenant

ROOT = Path(__file__).resolve().parent.parent
SUBJECT = "0x00000000000000000000000000000000000000aa"
NOW = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def _load() -> ModuleType:
    """Load the script by path: scripts/ is a directory of CLIs, not a package."""
    path = ROOT / "scripts" / "deletion_test.py"
    spec = importlib.util.spec_from_file_location("deletion_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script() -> ModuleType:
    return _load()


@pytest.fixture
def seeded_db(tmp_path: Path) -> Iterator[Path]:
    path = tmp_path / "memory.db"
    store = MemoryStore.open(path)
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
    store.close()
    yield path


# ---- what counts as a usable verdict -------------------------------------


def test_an_empty_verdict_is_not_usable(script: ModuleType) -> None:
    empty = Verdict(counterparty="cp:base:0xaa", standing="thin", confidence=None, basis=())
    assert script._is_usable(empty) is False


@pytest.mark.parametrize(
    ("standing", "confidence", "has_basis", "why"),
    [
        ("grounded", None, False, "a standing other than thin"),
        ("thin", 0.0, False, "any confidence at all, including zero"),
        ("thin", None, True, "a single observation in the basis"),
    ],
)
def test_anything_the_engine_could_act_on_is_usable(
    script: ModuleType,
    standing: str,
    confidence: float | None,
    has_basis: bool,
    why: str,
) -> None:
    """Each of these means the engine spoke without the record. All are failures."""
    from apps.agent.judge.verdict import BasisItem

    basis = (
        (
            BasisItem(
                observation_id="o1",
                kind="erc8004_feedback",
                occurred_at="2026-09-01T00:00:00.000Z",
                content_hash="sha256:x",
                source="base:test",
                reviewer=None,
                corroborated=False,
                weight=1.0,
            ),
        )
        if has_basis
        else ()
    )
    verdict = Verdict(
        counterparty="cp:base:0xaa",
        standing=standing,  # type: ignore[arg-type]
        confidence=confidence,
        basis=basis,
    )
    assert script._is_usable(verdict) is True, why


# ---- the gate, end to end ------------------------------------------------


def test_the_gate_passes_when_memory_off_says_nothing(
    script: ModuleType, seeded_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = script.main(["--agent", SUBJECT, "--db", str(seeded_db)])
    out = capsys.readouterr().out

    assert code == 0
    assert "memory ON" in out
    assert "memory OFF" in out
    assert "NO_BASIS" in out
    assert "PASS" in out
    # The record was read, so the memory-on side must actually have something.
    assert "basis=3" in out


def test_the_gate_fails_when_memory_off_produces_a_verdict(
    script: ModuleType,
    seeded_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The tripwire, tripped.

    If the engine ever answers from a null adapter, the build must go red rather
    than printing PASS over a broken claim.
    """
    real = script.evaluate

    def answers_without_memory(
        store: object, chain: str, address: str, **kwargs: object
    ) -> Verdict:
        if isinstance(store, NullStore):
            return Verdict(
                counterparty=counterparty_tenant(chain, address),
                standing="grounded",
                confidence=0.9,
                basis=(),
            )
        return real(store, chain, address, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(script, "evaluate", answers_without_memory)

    code = script.main(["--agent", SUBJECT, "--db", str(seeded_db)])
    out = capsys.readouterr().out

    assert code == 1
    assert "FAIL" in out
    assert "PASS" not in out


def test_the_gate_does_not_alter_the_record(script: ModuleType, seeded_db: Path) -> None:
    """Proving the point must not change what is being measured."""
    script.main(["--agent", SUBJECT, "--db", str(seeded_db)])

    store = MemoryStore.open(seeded_db)
    try:
        with store.use(counterparty_tenant("base", SUBJECT)):
            assert store.verdict() is None
    finally:
        store.close()
