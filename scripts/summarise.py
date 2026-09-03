"""Evaluate every indexed counterparty and record what Cairn currently holds.

Two things happen here, and both are ordinary product behaviour rather than
bookkeeping for a web page.

Every counterparty in the indexed set is judged, which writes its verdict to HOT
and journals the evaluation. Until this runs, the HOT tier is empty because no
verdict has ever been asked for.

The result is summarised into `cairn:self`, the tenant the brief reserves for
Cairn's own operating state. The landing page reads that summary through the
API, so every figure on the page is a count of rows Cairn actually holds rather
than a number typed into a template.

    python scripts/summarise.py --db data/memory.db
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
from apps.agent.judge.methodology import published
from apps.agent.judge.verdict import evaluate, reviewer_weight
from apps.agent.memory.store import SELF_TENANT, MemoryCapReachedError, MemoryStore

# Secrets live in .env.local; the scripts read os.environ. Bridge the two
# before anything asks for a key.
load_env()

SUMMARY_KEY = "site-summary"
POLICY_KEY = "scoring-policy"


def _address_of(tenant: str) -> str:
    """cp:base:0xabc -> 0xabc"""
    return tenant.split(":")[-1]


def build(store: MemoryStore, *, write_limit: int = 0) -> dict[str, Any]:
    counterparties = store.dossiers("cp:")
    reviewers = store.dossiers("rv:")

    # Who has spoken about which agent, across the whole indexed set. The API
    # cannot afford this scan per request, but a reviewer's weight is only
    # meaningful against it, so it is computed once here.
    witnessed: dict[Any, set[str]] = defaultdict(set)
    witnessed_by_tenant: dict[str, set[str]] = defaultdict(set)
    agents_of_tenant: dict[str, set[Any]] = defaultdict(set)
    kinds: Counter[str] = Counter()
    examples: dict[str, dict[str, Any]] = {}
    recent: list[dict[str, Any]] = []

    for tenant in counterparties:
        with store.use(tenant):
            for row in store.observations():
                kind = str(row.get("kind", ""))
                kinds[kind] += 1
                body = row.get("body") if isinstance(row.get("body"), dict) else {}
                if isinstance(body, dict):
                    agent_id = body.get("agent_id")
                    client = body.get("client")
                    if agent_id is not None and isinstance(client, str):
                        witnessed[agent_id].add(client.lower())
                        witnessed_by_tenant[tenant].add(client.lower())
                        agents_of_tenant[tenant].add(agent_id)
                if kind and kind not in examples:
                    examples[kind] = {
                        "kind": kind,
                        "source": row.get("source"),
                        "content_hash": row.get("content_hash"),
                        "occurred_at": row.get("occurred_at"),
                        "tx_hash": body.get("tx_hash") if isinstance(body, dict) else None,
                        "counterparty": tenant,
                    }
                recent.append(
                    {
                        "at": str(row.get("occurred_at", "")),
                        "kind": kind,
                        "counterparty": tenant,
                    }
                )

    # Claims live in the claimant's own dossier, so a total that skipped them
    # would undercount what Cairn holds by more than a third.
    for tenant in reviewers:
        with store.use(tenant):
            for row in store.observations():
                kind = str(row.get("kind", ""))
                kinds[kind] += 1
                if kind and kind not in examples:
                    body = row.get("body") if isinstance(row.get("body"), dict) else {}
                    examples[kind] = {
                        "kind": kind,
                        "source": row.get("source"),
                        "content_hash": row.get("content_hash"),
                        "occurred_at": row.get("occurred_at"),
                        "tx_hash": body.get("tx_hash") if isinstance(body, dict) else None,
                        "counterparty": tenant,
                    }

    # Every counterparty is judged, because the standings tally has to cover
    # the whole indexed set. Only the first `write_limit` are persisted to HOT:
    # the free tier cannot hold a verdict for all seventy alongside the journal
    # they are derived from, and a verdict is recomputable while an observation
    # is not. HOT therefore means "under active evaluation", which is what the
    # tier was specified to mean.
    standings: Counter[str] = Counter()
    ranked = sorted(
        counterparties,
        key=lambda t: -len(witnessed_by_tenant.get(t, ())),
    )
    persist = set(ranked[:write_limit]) if write_limit > 0 else set()
    agent_standing: dict[Any, str] = {}
    for tenant in counterparties:
        verdict = evaluate(store, "base", _address_of(tenant), write=tenant in persist)
        standings[verdict.standing] += 1
        for agent_id in agents_of_tenant.get(tenant, ()):
            agent_standing[agent_id] = verdict.standing

    # The published methodology belongs in REFERENCE: it changes rarely, and it
    # is the kind of thing a reader should be able to fetch rather than infer.
    with store.use(SELF_TENANT):
        store.put_reference(POLICY_KEY, published())

    weights = []
    contradicted_by_reviewer: dict[str, int] = {}
    for tenant in reviewers:
        address = _address_of(tenant)
        weight = reviewer_weight(store, address, witnessed=witnessed)
        weights.append(weight)
        with store.use(tenant):
            claims = [r for r in store.observations() if r.get("kind") == "erc8004_claim"]
        contradicted = 0
        for claim in claims:
            body = claim.get("body")
            if not isinstance(body, dict):
                continue
            if agent_standing.get(body.get("agent_id")) == "suspect":
                contradicted += 1
        contradicted_by_reviewer[address.lower()] = contradicted
    weights.sort(key=lambda w: (-w.claims, w.address))

    recent.sort(key=lambda row: row["at"], reverse=True)

    summary: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "counterparties": len(counterparties),
        "reviewers": len(reviewers),
        "observations": int(sum(kinds.values())),
        "observation_kinds": dict(kinds),
        "observation_examples": list(examples.values()),
        "tiers": store.tier_counts(),
        "standings": {
            name: standings.get(name, 0)
            for name in ("grounded", "thin", "suspect", "dormant")
        },
        "reviewer_example": weights[0].as_payload() if weights else None,
        "reviewers_detail": [
            {**w.as_payload(), "contradicted": contradicted_by_reviewer.get(w.address, 0)}
            for w in weights
        ],
        "reviewers_provisional": sum(1 for w in weights if w.provisional),
        "recent": recent[:5],
    }

    with store.use(SELF_TENANT):
        # cairn:self HOT is shared: the API keeps recent lookups there too, and
        # a wholesale rewrite would silently drop them.
        held = store.verdict() or {}
        store.put_verdict({**held, "summary": summary})
        store.put_reference(SUMMARY_KEY, summary)

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/memory.db")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--write-limit",
        type=int,
        default=0,
        help="persist this many verdicts to HOT, most-witnessed first (0 writes none)",
    )
    args = parser.parse_args(argv)

    store = MemoryStore.open(args.db)
    try:
        # The sweep rewrites 70 HOT rows, which churns the SDK's FTS indexes.
        # Compacting on the way in buys the headroom to finish.
        freed = store.compact()
        if freed:
            print(f"  compacted       {freed:,} bytes reclaimed")
        summary = build(store, write_limit=args.write_limit)
        store.compact()
    except MemoryCapReachedError as cap:
        print(f"  {cap}")
        print("  The indexed set is scoped to the free tier. Nothing was truncated.")
        return 1
    finally:
        store.close()

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"  counterparties  {summary['counterparties']}")
    print(f"  reviewers       {summary['reviewers']}")
    print(f"  observations    {summary['observations']}")
    print(f"  kinds           {summary['observation_kinds']}")
    print(f"  tiers           {summary['tiers']}")
    print(f"  standings       {summary['standings']}")
    print(f"  reviewer sample {summary['reviewer_example']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
