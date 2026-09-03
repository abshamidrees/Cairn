"""Cairn's read API, mounted on the same machine as memory.db.

One rule shapes this module: `?memory=off` genuinely bypasses the memory layer.
It swaps `MemoryStore` for `NullStore` before the request reaches the engine, so
the empty state is produced by an engine that really has nothing to read. A judge
opening the network tab sees a server that answered without its record, not a
front end pretending. Faking it client-side would be the fastest way to lose the
one criterion this project is built around.

The store is opened per request and closed after it. SQLite connections are not
shareable across the threadpool FastAPI runs sync handlers in, and a dossier read
is short enough that a pool would be complexity without a reason.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from apps.agent.judge.verdict import Verdict, evaluate
from apps.agent.memory.store import (
    SELF_TENANT,
    MemoryCapReachedError,
    MemoryStore,
    NullStore,
    Store,
    counterparty_tenant,
    reviewer_tenant,
)

DEFAULT_DB = os.environ.get("SIBYL_DB") or "data/memory.db"

#: Bottom to top, the same order the mark stacks its stones in.
TIERS = ("ARCHIVE", "REFERENCE", "COLD", "WARM", "HOT")

Grounding = Literal["grounded", "thin", "suspect", "dormant"]

app = FastAPI(
    title="Cairn",
    summary="A record, not a rating.",
    version="0.1.0",
)

# The web app is served from a different origin in development and from the
# usecairn.xyz subdomains in production.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://([a-z]+\.)?usecairn\.xyz",
    allow_methods=["GET"],
    allow_headers=["*"],
)


@contextmanager
def _store_for(memory: str) -> Iterator[Store]:
    """Hand back the real adapter, or genuinely none at all.

    This is the entire implementation of `?memory=off`. Nothing downstream
    branches on it, and nothing downstream can tell which one it received.
    """
    if memory == "off":
        yield NullStore()
        return

    store = MemoryStore.open(DEFAULT_DB)
    try:
        yield store
    finally:
        store.close()


def _tilt(observation_id: str) -> float:
    """Deterministic tilt, derived from the observation id.

    A stack that reshuffles on every render looks like a toy. Same id, same
    lean, forever, and the front end derives it identically.
    """
    digest = hashlib.sha256(observation_id.encode("utf-8")).hexdigest()
    return round((int(digest[:8], 16) % 500) / 100 - 2.5, 2)


def _grounding_of(
    observation_id: str,
    *,
    corroborated: bool,
    contradicted: set[str],
) -> Grounding:
    """Fill encodes grounding, and only ever what the record can support."""
    if observation_id in contradicted:
        return "suspect"
    return "grounded" if corroborated else "thin"


def _stone(
    *,
    stone_id: str,
    tier: str,
    weight: float,
    grounding: Grounding,
    label: str,
    detail: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": stone_id,
        "tier": tier,
        "weight": round(max(0.0, min(1.0, weight)), 4),
        "grounding": grounding,
        "tilt": _tilt(stone_id),
        "label": label,
        "detail": detail,
    }


def _dossier_payload(store: Store, chain: str, address: str, memory: str) -> dict[str, Any]:
    """The whole dossier, arranged by the tier each row actually lives in."""
    verdict: Verdict = evaluate(store, chain, address, write=False)
    tenant = counterparty_tenant(chain, address)

    contradicted: set[str] = {
        oid for c in verdict.contradictions for oid in c.observation_ids if oid
    }
    stones: dict[str, list[dict[str, Any]]] = {tier: [] for tier in TIERS}

    # COLD, one stone per observation. This is the ledger.
    for item in verdict.basis:
        stones["COLD"].append(
            _stone(
                stone_id=item.observation_id,
                tier="COLD",
                weight=item.weight,
                grounding=_grounding_of(
                    item.observation_id,
                    corroborated=item.corroborated,
                    contradicted=contradicted,
                ),
                label=item.kind,
                detail={
                    "occurred_at": item.occurred_at,
                    "source": item.source,
                    "content_hash": item.content_hash,
                    "reviewer": item.reviewer,
                    "corroborated": item.corroborated,
                    # So the basis is followable back to the chain it came from.
                    "tx_hash": item.tx_hash,
                },
            )
        )

    # WARM, the behaviour that repeated often enough to become a durable fact.
    with store.use(tenant):
        for entity in store.facts():
            body = entity.get("body") if isinstance(entity.get("body"), dict) else {}
            occurrences = body.get("n", 0) if isinstance(body, dict) else 0
            stones["WARM"].append(
                _stone(
                    stone_id=str(entity.get("id", entity.get("name", ""))),
                    tier="WARM",
                    weight=min(1.0, float(occurrences) / 10.0) if occurrences else 0.3,
                    grounding="grounded" if occurrences >= 3 else "thin",
                    label=str(entity.get("name", "")),
                    detail={
                        "category": entity.get("category"),
                        "n": occurrences,
                        "first_seen": body.get("first_seen") if isinstance(body, dict) else None,
                        "last_seen": body.get("last_seen") if isinstance(body, dict) else None,
                    },
                )
            )

        # ARCHIVE, recovered from the journal because the client cannot read an
        # archived row back under any status or search tier.
        for record in store.archived():
            stones["ARCHIVE"].append(
                _stone(
                    stone_id=str(record.get("id", "")),
                    tier="ARCHIVE",
                    weight=0.35,
                    grounding="dormant",
                    label=str(record.get("name", "")),
                    detail={
                        "reason": record.get("reason", "evidence aged out"),
                        "retired_at": record.get("ts"),
                    },
                )
            )

    # HOT, the live verdict itself. The keystone, and there is only ever one.
    if verdict.basis:
        stones["HOT"].append(
            _stone(
                stone_id=f"verdict:{tenant}",
                tier="HOT",
                weight=verdict.confidence if verdict.confidence is not None else 0.2,
                grounding=verdict.standing,
                label="verdict",
                detail={
                    "standing": verdict.standing,
                    "confidence": verdict.confidence,
                    "evaluated_at": verdict.evaluated_at,
                },
            )
        )

    grounded = sum(1 for s in stones["COLD"] if s["grounding"] == "grounded")

    # What Cairn published about this counterparty on Base, if anything. An
    # attestation is a fact about the agent, so it is read out of the dossier
    # rather than out of a side table the verdict cannot see.
    with store.use(tenant):
        published = store.fact("attestation", "latest")
        contract = store.reference("attestation-contract")
    attestation: dict[str, Any] | None = None
    if published is not None:
        body = published.get("body")
        tx = body.get("value") if isinstance(body, dict) else None
        if isinstance(tx, str) and tx:
            attestation = {
                "tx_hash": tx,
                "explorer_url": f"https://basescan.org/tx/{tx}",
                "contract": (contract or {}).get("address"),
                "chain_id": (contract or {}).get("chain_id"),
            }

    return {
        "counterparty": tenant,
        "attestation": attestation,
        "memory": "off" if memory == "off" else "on",
        "verdict": verdict.as_payload(),
        "tiers": TIERS,
        "stones": stones,
        "counts": {
            "observations": len(stones["COLD"]),
            "grounded": grounded,
        },
    }


@app.get("/v1/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "db": DEFAULT_DB}


RECENT_KEY = "recent-lookups"
RECENT_LIMIT = 8


def _remember_lookup(store: Store, tenant: str) -> None:
    """Keep the last few lookups in Cairn's own dossier, not in a browser.

    Part 8 asks for recent lookups persisted in memory rather than
    localStorage, so they live in `cairn:self` where the rest of Cairn's
    operating state does. HOT is rewritten in place, so this is bounded.

    Best effort on purpose. A convenience list must never be the reason a read
    fails, and the free tier's cap is a real thing that fires.
    """
    try:
        with store.use(SELF_TENANT):
            held = store.verdict() or {}
            recent = held.get("recent_lookups")
            rows: list[str] = (
                [r for r in recent if isinstance(r, str)] if isinstance(recent, list) else []
            )
            rows = [tenant, *[r for r in rows if r != tenant]][:RECENT_LIMIT]
            store.put_verdict({**held, "recent_lookups": rows})
    except MemoryCapReachedError:
        return


@app.get("/v1/recent")
def recent(memory: str = Query("on", pattern="^(on|off)$")) -> dict[str, Any]:
    """The last few counterparties anyone looked up, from Cairn's own dossier."""
    with _store_for(memory) as store, store.use(SELF_TENANT):
        held = store.verdict() or {}
    rows = held.get("recent_lookups")
    return {
        "memory": "off" if memory == "off" else "on",
        "recent": [r for r in rows if isinstance(r, str)] if isinstance(rows, list) else [],
    }


@app.get("/v1/reviewer/{address}")
def reviewer(
    address: str,
    memory: str = Query("on", pattern="^(on|off)$"),
) -> dict[str, Any]:
    """What a claimant has said, and how much of it anyone else witnessed.

    The weight is read from the summary rather than recomputed, because a
    reviewer's weight is only meaningful against the whole indexed set and a
    number measured against one dossier would be a different number wearing the
    same name.
    """
    tenant = reviewer_tenant(address)
    with _store_for(memory) as store:
        with store.use(tenant):
            claims = [row for row in store.observations() if row.get("kind") == "erc8004_claim"]
        with store.use(SELF_TENANT):
            summary = store.reference("site-summary") or {}

    detail = None
    for row in summary.get("reviewers_detail") or []:
        if isinstance(row, dict) and str(row.get("address", "")).lower() == address.lower():
            detail = row
            break

    return {
        "reviewer": tenant,
        "address": address.lower(),
        "memory": "off" if memory == "off" else "on",
        "known": bool(claims) or detail is not None,
        "claims": claims,
        "weight": detail,
        "generated_at": summary.get("generated_at"),
    }


@app.get("/v1/stats")
def stats(memory: str = Query("on", pattern="^(on|off)$")) -> dict[str, Any]:
    """What Cairn currently holds, read from its own dossier.

    Written by scripts/summarise.py into `cairn:self`, the tenant reserved for
    Cairn's own operating state. Every figure the landing page shows comes from
    here, so a number on the page is a count of rows in the database rather than
    a constant in a template. With memory off there is nothing to report, which
    is the honest answer and the one the page renders.
    """
    with _store_for(memory) as store, store.use(SELF_TENANT):
        summary = store.reference("site-summary")
    if summary is None:
        return {"memory": "off" if memory == "off" else "on", "available": False}
    return {"memory": "off" if memory == "off" else "on", "available": True, **summary}


@app.get("/v1/lookup/{address}")
def lookup(
    address: str,
    chain: str = "base",
    memory: str = Query("on", pattern="^(on|off)$"),
) -> dict[str, Any]:
    """The verdict for one counterparty, with the basis it rests on.

    Read-only. An earlier version recorded the verdict here, on the reasoning
    that a lookup is what makes one live. That was wrong: the free tier has a
    hard cap, and a GET that writes turns a full database into a 500 on every
    read. A verdict is arithmetic over the journal and can be recomputed at any
    time, so the read path never needs to persist it. Writes happen where they
    can be allowed to fail: scripts/summarise.py and the agent's own loop.
    """
    with _store_for(memory) as store:
        verdict = evaluate(store, chain, address, write=False)
    return {
        "counterparty": verdict.counterparty,
        "memory": "off" if memory == "off" else "on",
        **verdict.as_payload(),
    }


@app.get("/v1/dossier/{address}")
def dossier(
    address: str,
    chain: str = "base",
    memory: str = Query("on", pattern="^(on|off)$"),
) -> dict[str, Any]:
    """Everything Cairn holds about one counterparty, arranged by tier."""
    with _store_for(memory) as store:
        payload = _dossier_payload(store, chain, address, memory)
        if memory != "off":
            _remember_lookup(store, payload["counterparty"])
        return payload


@app.get("/v1/observations/{address}")
def observations(
    address: str,
    chain: str = "base",
    memory: str = Query("on", pattern="^(on|off)$"),
) -> dict[str, Any]:
    """The raw journal for one counterparty, oldest first."""
    with _store_for(memory) as store, store.use(counterparty_tenant(chain, address)):
        rows = store.observations()
    return {
        "counterparty": counterparty_tenant(chain, address),
        "memory": "off" if memory == "off" else "on",
        "observations": rows,
    }
