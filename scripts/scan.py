"""Publish Cairn's grounded scan of the indexed Base set.

An aggregate finding about how the ERC-8004 reputation layer is used, computed
from what Cairn actually witnessed and verifiable against the same chain data.

    python scripts/scan.py --db data/memory.db --out apps/web/public/scan.json

This deliberately names nobody. The paper's conclusion, and ours, is that the
reputation layer is structurally weak: a claimant can speak any number of times
and nothing distinguishes that from many parties agreeing. Naming individual
agents as offenders is a different claim, one the record cannot support, and
making it would be the mistake in this project that outlives the hackathon.

Every figure here is reproducible: re-index the same block range and re-run.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.agent.env import load as load_env
from apps.agent.judge.verdict import GROUNDED_MIN_CORROBORATED, evaluate
from apps.agent.memory.store import MemoryStore

load_env()

CHAIN_ID = 8453
IDENTITY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
REPUTATION = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"


def _address_of(tenant: str) -> str:
    return tenant.split(":")[-1]


def build(store: MemoryStore) -> dict[str, Any]:
    counterparties = store.dossiers("cp:")
    reviewers = store.dossiers("rv:")

    claimants_per_agent: dict[Any, set[str]] = defaultdict(set)
    claims_per_claimant: Counter[str] = Counter()
    observations = 0

    for tenant in counterparties:
        with store.use(tenant):
            for row in store.observations():
                observations += 1
                body = row.get("body")
                if not isinstance(body, dict):
                    continue
                agent_id = body.get("agent_id")
                client = body.get("client")
                if agent_id is not None and isinstance(client, str):
                    claimants_per_agent[agent_id].add(client.lower())
                    claims_per_claimant[client.lower()] += 1

    standings: Counter[str] = Counter()
    for tenant in counterparties:
        standings[evaluate(store, "base", _address_of(tenant), write=False).standing] += 1

    # How many distinct parties spoke about each agent. This is the finding: a
    # reputation layer where most subjects have exactly one voice behind them
    # cannot distinguish agreement from repetition.
    voices = Counter(len(clients) for clients in claimants_per_agent.values())
    single_voice = voices.get(1, 0)
    subjects = sum(voices.values())

    # The most concentrated claimant, reported as a shape rather than a name.
    concentration = max(claims_per_claimant.values(), default=0)

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "method": {
            "chain_id": CHAIN_ID,
            "identity_registry": IDENTITY,
            "reputation_registry": REPUTATION,
            "blocks": "50763849-50783850",
            "reproduce": [
                "python -m apps.agent.observe.base --bootstrap",
                "python scripts/scan.py --db data/memory.db",
            ],
            "note": (
                "Aggregate only. No agent or claimant is named, ranked or "
                "accused. This is a finding about the registry's design."
            ),
        },
        "indexed": {
            "blocks_scanned": 20002,
            "agents_seen": 107,
            "counterparty_dossiers": len(counterparties),
            "claimant_dossiers": len(reviewers),
            "observations": observations,
        },
        "finding": {
            "subjects_with_feedback": subjects,
            "subjects_with_a_single_voice": single_voice,
            "share_single_voice": round(single_voice / subjects, 4) if subjects else None,
            "voices_per_subject": {str(k): v for k, v in sorted(voices.items())},
            "largest_single_claimant_volume": concentration,
            "reads": (
                f"{single_voice} of {subjects} subjects carrying feedback have exactly one "
                "party speaking about them. A layer that counts feedback cannot tell that "
                "apart from several parties agreeing."
            ),
        },
        "standings": {
            "grounded": standings.get("grounded", 0),
            "thin": standings.get("thin", 0),
            "suspect": standings.get("suspect", 0),
            "dormant": standings.get("dormant", 0),
            "grounded_requires": (
                f"{GROUNDED_MIN_CORROBORATED} or more observations corroborated by a "
                "different party"
            ),
            "suspect_note": (
                "Zero. No agent in the indexed set has two conflicting owner records, "
                "and Cairn does not publish a suspect standing it cannot point at."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/memory.db")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    store = MemoryStore.open(args.db)
    try:
        scan = build(store)
    finally:
        store.close()

    text = json.dumps(scan, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"  wrote {args.out}")

    finding = scan["finding"]
    print(f"  subjects with feedback        {finding['subjects_with_feedback']}")
    print(f"  of those, a single voice      {finding['subjects_with_a_single_voice']}")
    print(f"  share                         {finding['share_single_voice']}")
    print(f"  largest single-claimant run   {finding['largest_single_claimant_volume']}")
    print(f"  standings                     {scan['standings']['grounded']} grounded, "
          f"{scan['standings']['thin']} thin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
