"""Build a synthetic dossier for the deletion test to run against in CI.

    python scripts/build_fixture.py --out .ci/memory.db

The real database is gitignored and holds addresses indexed from Base. None of
that belongs in the repository: it is third-party data, it is 4.5 MB, and CI has
no Base RPC to rebuild it with. So the fixture is generated instead of committed,
from addresses that are obviously not real.

The shape matters. Three independent claimants is the smallest record that
reaches `grounded`, which is what gives the deletion test something to lose. A
fixture that evaluated to `thin` would still pass the gate, because the gate only
asserts the memory-off run is unusable, and it would prove nothing at all.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.agent.memory.store import MemoryStore, Observation, counterparty_tenant

#: Deliberately unmistakable. No address here is or could be a real agent.
SUBJECT = "0x00000000000000000000000000000000000000aa"
CLAIMANTS = (
    "0x00000000000000000000000000000000000000a1",
    "0x00000000000000000000000000000000000000b2",
    "0x00000000000000000000000000000000000000c3",
)

REPUTATION = "base:0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"
IDENTITY = "base:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"

#: Fixed, so the fixture is byte-comparable between runs and the verdict it
#: produces does not drift with the calendar into `dormant`.
WHEN = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def _feedback(client: str) -> Observation:
    return Observation(
        kind="erc8004_feedback",
        pattern="feedback-untagged",
        source=REPUTATION,
        content_hash=f"sha256:{client}:{WHEN.isoformat()}",
        occurred_at=WHEN,
        body={"agent_id": 1, "client": client},
        reviewer=client,
    )


def _registration() -> Observation:
    return Observation(
        kind="erc8004_registration",
        pattern="registered-on-erc8004",
        source=IDENTITY,
        content_hash="sha256:reg:1:fixture",
        occurred_at=WHEN,
        body={"agent_id": 1, "owner": CLAIMANTS[0], "registration_available": True},
    )


def build(path: Path) -> str:
    """Write the fixture and return the subject address."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    store = MemoryStore.open(path)
    try:
        with store.use(counterparty_tenant("base", SUBJECT)):
            store.record_observation(_registration())
            for claimant in CLAIMANTS:
                store.record_observation(_feedback(claimant))
    finally:
        store.close()
    return SUBJECT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(".ci/memory.db"))
    args = parser.parse_args(argv)

    subject = build(args.out)
    print(f"  wrote     {args.out} ({args.out.stat().st_size:,} bytes)")
    print(f"  subject   {subject}")
    print(f"  claimants {len(CLAIMANTS)} independent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
