"""Confirm Sibyl Memory runs locally, with no credentials and no network.

Phase 0 gate. Every load-bearing claim in this repo rests on `MemoryClient.local()`
behaving as an offline, credential-free store with isolated tenants. Proving that
before any adapter exists means a later failure is our bug, not the SDK's.

Run:  python scripts/verify_memory.py
"""

from __future__ import annotations

import argparse
import socket
import tempfile
from pathlib import Path
from typing import Any

from sibyl_memory_client import MemoryClient

COUNTERPARTY_A = "cp:base:0x00000000000000000000000000000000000000aa"
COUNTERPARTY_B = "cp:base:0x00000000000000000000000000000000000000bb"


class NetworkBlockedError(Exception):
    """Raised if anything attempts a socket connection during the probe."""


def _block_network() -> None:
    """Hard-fail any outbound socket so 'works offline' is proven, not assumed."""

    def _deny(*_args: object, **_kwargs: object) -> None:
        raise NetworkBlockedError("a network call was attempted")

    socket.socket.connect = _deny  # type: ignore[method-assign]
    socket.create_connection = _deny  # type: ignore[assignment]


def probe(db_path: Path) -> dict[str, Any]:
    """Exercise all five tiers plus tenant isolation against a fresh database."""
    # No account_id, session_token or credentials_claim. That is the point.
    m = MemoryClient.local(db_path)

    m.set_tenant(COUNTERPARTY_A)
    m.set_state("verdict", {"standing": "thin", "confidence": None})
    m.set_entity("identity", "declared-service", {"kind": "escrow", "n": 1})
    m.set_reference("policy-version", {"version": "0.1.0"})
    event_id = m.write_event(
        evaluated={"counterparty": COUNTERPARTY_A},
        acted={"wrote": "verdict"},
        forward=[{"recheck": COUNTERPARTY_A}],
    )

    state = m.get_state("verdict")
    entity = m.get_entity("identity", "declared-service")
    reference = m.get_reference("policy-version")
    events = m.read_events(limit=5)
    hits = m.search("escrow")

    # Tenant isolation: B must not see A's rows. This is what makes a dossier
    # a dossier rather than a shared notepad.
    m.set_tenant(COUNTERPARTY_B)
    leaked = m.list_entities("identity")

    # archive_entity MOVES the row out of the entities table. It is not a status
    # flag: after archiving, list_entities returns nothing under any status and
    # get_entity raises NotFoundError. The archive is not readable through the
    # client API at all, and "archive" is not a valid search tier, so the reason
    # cannot be read back. Cairn therefore journals every archival itself.
    m.set_tenant(COUNTERPARTY_A)
    receipt = m.archive_entity("identity", "declared-service", reason="phase 0 probe")
    still_listed = m.list_entities("identity")

    result = {
        "tier": m.get_tier(),
        "schema_version": m.schema_version(),
        "tenant_roundtrip": m.get_tenant() == COUNTERPARTY_A,
        "arbitrary_tenant_id_accepted": True,
        "hot_state": state is not None,
        "warm_entity": entity is not None,
        "reference": reference is not None,
        "cold_event_id": event_id,
        "cold_events_read": len(events),
        "search_hits": len(list(hits)),
        "tenant_isolation_holds": len(leaked) == 0,
        "archive_receipt_ids": sorted(receipt),
        "archive_removes_entity": len(still_listed) == 0,
        "free_tier_status": m.free_tier_status(),
    }

    # SQLite keeps the file handle open, and Windows will not delete a locked
    # file, so the probe must release it before the caller cleans up.
    m.storage.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=None, help="database path (default: temp)")
    args = parser.parse_args()

    _block_network()

    if args.db is not None:
        result = probe(args.db)
    else:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            result = probe(Path(tmp) / "probe.db")

    checks = {
        "tenant id accepts our cp:<chain>:<address> scheme": result["tenant_roundtrip"],
        "HOT   set_state / get_state": result["hot_state"],
        "WARM  set_entity / get_entity": result["warm_entity"],
        "COLD  write_event / read_events": result["cold_events_read"] > 0,
        "REFERENCE set_reference / get_reference": result["reference"],
        "ARCHIVE archive_entity moves the row out": (
            result["archive_receipt_ids"] == ["archived_id", "original_id"]
            and result["archive_removes_entity"]
        ),
        "FTS5 search returns hits": result["search_hits"] > 0,
        "tenant isolation holds": result["tenant_isolation_holds"],
    }

    width = max(len(k) for k in checks)
    for label, ok in checks.items():
        print(f"  {label.ljust(width)}   {'ok' if ok else 'FAILED'}")

    print()
    print(f"  tier            {result['tier']}")
    print(f"  schema version  {result['schema_version']}")
    print(f"  free tier       {result['free_tier_status']}")
    print()

    if all(checks.values()):
        print("  MemoryClient.local() works offline with no credentials.  PASS")
        return 0
    print("  Sibyl Memory did not behave as the brief assumes.  FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
