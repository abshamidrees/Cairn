"""Drive the Virtuals ACP CLI, and act as a neutral Evaluator on real jobs.

Everything here goes through `@virtuals-protocol/acp-cli` by subprocess with
`--json`. There is no second chain client for ACP: the CLI already holds the
agent's signer, and reimplementing its escrow calls would mean maintaining a
parallel understanding of a protocol we do not control.

Cairn occupies two roles on one job.

As **provider** it sells `Counterparty dossier`: the requirement is a
counterparty address, and the deliverable is the dossier JSON that
`judge/verdict.py` produced, including the observation ids the verdict rests on.

As **Evaluator** it decides whether a deliverable is acceptable. That decision is
the same arithmetic the rest of the product uses, never a model call and never a
rubber stamp: a deliverable is accepted when it carries a basis Cairn can match
against its own record, and rejected with a reason naming what was missing.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from apps.agent.judge.verdict import evaluate
from apps.agent.memory.store import Store

#: Base mainnet. `IS_TESTNET=true` in the environment swaps the CLI to 84532.
CHAIN_ID = 8453

OFFERING = "Counterparty dossier"


class AcpError(RuntimeError):
    """The CLI exited non-zero, or answered with something that was not JSON."""


class Runner(Protocol):
    """How the CLI gets invoked. Injected so tests never shell out."""

    def __call__(self, args: Sequence[str]) -> str: ...


def _subprocess_runner(args: Sequence[str]) -> str:
    executable = shutil.which("acp")
    if executable is None:
        raise AcpError("the acp CLI is not on PATH: npm i -g @virtuals-protocol/acp-cli")
    completed = subprocess.run(  # noqa: S603
        [executable, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise AcpError(f"acp {' '.join(args)} failed: {detail[:400]}")
    return completed.stdout


@dataclass(frozen=True)
class Deliverable:
    """What Cairn hands back when it sells a dossier."""

    counterparty: str
    standing: str
    confidence: float | None
    basis: tuple[str, ...]
    methodology: str

    def as_payload(self) -> dict[str, Any]:
        return {
            "counterparty": self.counterparty,
            "standing": self.standing,
            "confidence": self.confidence,
            "basis": list(self.basis),
            "methodology": self.methodology,
        }


@dataclass(frozen=True)
class Decision:
    """An Evaluator's answer, and the reason it can point at."""

    accept: bool
    reason: str


class Acp:
    """A thin, typed shell around the CLI."""

    def __init__(self, runner: Runner | None = None, *, chain_id: int = CHAIN_ID) -> None:
        self._run_cli: Runner = runner or _subprocess_runner
        self._chain_id = chain_id

    def _json(self, *args: str) -> object:
        """Every command is asked for `--json`, because parsing tables is a bug."""
        raw = self._run_cli([*args, "--json"])
        text = raw.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            # The CLI prints human text on some paths even with --json. Surface
            # it rather than pretending an empty result came back.
            raise AcpError(f"acp {' '.join(args)} did not return JSON: {text[:300]}") from exc

    # ---- identity ---------------------------------------------------------

    def whoami(self) -> dict[str, Any]:
        found = self._json("agent", "whoami")
        return found if isinstance(found, dict) else {}

    def offerings(self) -> list[dict[str, Any]]:
        found = self._json("offering", "list")
        if isinstance(found, list):
            return [row for row in found if isinstance(row, dict)]
        return []

    # ---- jobs -------------------------------------------------------------

    def jobs(self) -> list[dict[str, Any]]:
        # `job list` takes no chain flag, unlike every other job command. Passing
        # one makes the CLI exit non-zero on an unknown option.
        found = self._json("job", "list")
        rows: object = found.get("data") if isinstance(found, dict) else found
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    def history(self, job_id: str) -> dict[str, Any]:
        found = self._json("job", "history", "--job-id", job_id, "--chain-id", str(self._chain_id))
        return found if isinstance(found, dict) else {}

    # ---- as provider ------------------------------------------------------

    def set_budget(self, job_id: str, amount: str) -> dict[str, Any]:
        found = self._json(
            "provider", "set-budget",
            "--job-id", job_id,
            "--amount", amount,
            "--chain-id", str(self._chain_id),
        )
        return found if isinstance(found, dict) else {}

    def submit(self, job_id: str, deliverable: Deliverable) -> dict[str, Any]:
        found = self._json(
            "provider", "submit",
            "--job-id", job_id,
            "--deliverable", json.dumps(deliverable.as_payload(), separators=(",", ":")),
            "--chain-id", str(self._chain_id),
        )
        return found if isinstance(found, dict) else {}

    # ---- as client, and as Evaluator -------------------------------------

    def create_job(self, provider: str, requirements: dict[str, Any]) -> dict[str, Any]:
        found = self._json(
            "client", "create-job",
            "--provider", provider,
            "--offering-name", OFFERING,
            "--requirements", json.dumps(requirements, separators=(",", ":")),
            "--chain-id", str(self._chain_id),
        )
        return found if isinstance(found, dict) else {}

    def complete(self, job_id: str, reason: str) -> dict[str, Any]:
        """Approve a deliverable. This is the Evaluator's accept path."""
        found = self._json(
            "client", "complete",
            "--job-id", job_id,
            "--chain-id", str(self._chain_id),
            "--reason", reason,
        )
        return found if isinstance(found, dict) else {}

    def reject(self, job_id: str, reason: str) -> dict[str, Any]:
        """Refuse a deliverable, naming what was missing."""
        found = self._json(
            "client", "reject",
            "--job-id", job_id,
            "--chain-id", str(self._chain_id),
            "--reason", reason,
        )
        return found if isinstance(found, dict) else {}


# ---- what Cairn sells, and how it judges what it is sold -----------------


def build_deliverable(store: Store, address: str, *, chain: str = "base") -> Deliverable:
    """Produce the dossier a buyer paid for, from the record Cairn holds."""
    verdict = evaluate(store, chain, address, write=False)
    return Deliverable(
        counterparty=verdict.counterparty,
        standing=verdict.standing,
        confidence=verdict.confidence,
        basis=tuple(item.observation_id for item in verdict.basis),
        methodology="https://docs.usecairn.xyz/methodology",
    )


def evaluate_deliverable(payload: object) -> Decision:
    """Decide whether a deliverable is acceptable, and say why.

    An Evaluator that approves everything is worth nothing, and one that judges
    on tone is worse. This checks the only thing that can be checked: whether
    the answer carries a basis, and whether its confidence is consistent with
    having one. A verdict claiming confidence with no observations behind it is
    the exact failure Cairn exists to catch, so it is refused.
    """
    if not isinstance(payload, dict):
        return Decision(False, "the deliverable was not a dossier")

    standing = payload.get("standing")
    if standing not in ("grounded", "thin", "suspect", "dormant"):
        return Decision(False, f"standing {standing!r} is not one Cairn recognises")

    basis = payload.get("basis")
    basis_list = basis if isinstance(basis, list) else []
    confidence = payload.get("confidence")

    if confidence is not None and not basis_list:
        return Decision(False, "confidence was asserted with no observations behind it")

    if standing == "grounded" and not basis_list:
        return Decision(False, "a grounded standing must name the observations it rests on")

    if standing == "suspect" and not basis_list:
        return Decision(False, "a suspect standing must name the contradiction it rests on")

    if not basis_list:
        # Thin with no basis is the honest answer to an unknown counterparty.
        return Decision(True, "no record held, and the deliverable says so rather than guessing")

    return Decision(
        True,
        f"{standing} with {len(basis_list)} observations named in the basis",
    )
