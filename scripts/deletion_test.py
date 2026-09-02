"""
deletion_test.py, proof that Cairn's memory layer is load-bearing.

The Sibyl Labs Hackathon gate is: remove the memory layer, does the project
still do what it claims? If yes it is a wrapper and it is disqualified.

This script answers that question in public. It runs the full verdict pipeline
twice against the same counterparty, once normally, once with the memory
adapter replaced by a null adapter whose every read returns empty and every
write is a no-op, and prints both results side by side.

It exits non-zero if the memory-off run ever produces a usable verdict, so it
can sit in CI and fail the build the day someone accidentally makes Cairn work
without its memory.

    python scripts/deletion_test.py --agent 0x...

Expected output:

  memory ON      standing=grounded  confidence=0.87  basis=41 observations
  memory OFF     standing=thin      confidence=-     basis=0  observations
                 ↳ verdict engine returned NO_BASIS

  Cairn's core function is unavailable without the memory layer.  PASS

The swap happens at the adapter boundary, not inside the engine. `evaluate`
takes a `Store` and cannot tell the two apart, which is what makes this a
one-line change rather than a branch in the verdict path. Both runs evaluate
with `write=False`, so proving the point does not itself alter the record.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.agent.judge.verdict import Verdict, evaluate
from apps.agent.memory.store import MemoryStore, NullStore

# The output shape in brief part 11 contains a glyph the Windows console
# cannot encode under cp1252, and this script has to run on the demo machine.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXIT_PASS = 0
EXIT_FAIL = 1

DEFAULT_DB = os.environ.get("SIBYL_DB", str(Path.home() / ".sibyl-memory" / "memory.db"))


def _row(label: str, verdict: Verdict) -> str:
    confidence = "-" if verdict.confidence is None else f"{verdict.confidence:.2f}"
    return (
        f"  {'memory ' + label:<15}"
        f"standing={verdict.standing:<10}"
        f"confidence={confidence:<6}"
        f"basis={len(verdict.basis):<2} observations"
    )


def _is_usable(verdict: Verdict) -> bool:
    """Whether a verdict is one an agent could actually act on.

    Memory off must produce none of these. A standing other than `thin`, any
    confidence at all, or a single observation in the basis all mean the engine
    found something to say without the record, and the gate has failed.
    """
    return bool(verdict.basis) or verdict.confidence is not None or verdict.standing != "thin"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prove Cairn's core function requires the memory layer."
    )
    parser.add_argument("--agent", required=True, help="counterparty address or agent id")
    parser.add_argument("--chain", default="base", help="chain the counterparty is on")
    parser.add_argument("--db", default=DEFAULT_DB, help="path to memory.db")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    now = datetime.now(UTC)
    store = MemoryStore.open(args.db)
    try:
        # The only difference between these two lines is the adapter.
        on = evaluate(store, args.chain, args.agent, now=now, write=False)
        off = evaluate(NullStore(), args.chain, args.agent, now=now, write=False)
    finally:
        store.close()

    usable = _is_usable(off)
    passed = not usable

    if args.json:
        print(
            json.dumps(
                {
                    "counterparty": on.counterparty,
                    "evaluated_at": on.evaluated_at,
                    "memory_on": on.as_payload(),
                    "memory_off": off.as_payload(),
                    "memory_off_usable": usable,
                    "passed": passed,
                },
                indent=2,
            )
        )
        return EXIT_PASS if passed else EXIT_FAIL

    # The counterparty and the timestamp are printed so a frame of the demo
    # video can be matched to a run.
    print()
    print(f"  counterparty   {on.counterparty}")
    print(f"  evaluated at   {on.evaluated_at}")
    print(f"  memory.db      {args.db}")
    print()
    print(_row("ON", on))
    print(_row("OFF", off))
    if off.no_basis:
        print(f"{'':17}↳ verdict engine returned NO_BASIS")
    print()

    if passed:
        print("  Cairn's core function is unavailable without the memory layer.  PASS")
        return EXIT_PASS

    print("  The memory-off run produced a usable verdict.  FAIL")
    print("  Cairn answered without reading its record, so the memory is not load-bearing.")
    return EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
