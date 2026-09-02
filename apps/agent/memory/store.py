"""Cairn's memory adapter, and the only module that imports sibyl_memory_client.

Everything else reaches Sibyl Memory through `Store`. That boundary is what makes
the deletion test a two-line swap: `NullStore` satisfies the same protocol with
empty reads and no-op writes.

The tier policy, from the brief part 10. Where a fact lives is information:

    HOT        set_state       the live verdict, rewritten in place
    WARM       set_entity      durable facts, and behaviour seen three times or more
    COLD       write_event     every observation, append-only, never rewritten
    REFERENCE  set_reference   things that rarely change
    ARCHIVE    archive_entity  entities whose evidence aged out, retired with a reason

Two behaviours of the SDK shape this module, both verified rather than assumed.

`get_entity` raises `NotFoundError` instead of returning None, so every read goes
through `_maybe_entity`.

`archive_entity` moves the row out of the entities table rather than flagging it.
Afterwards `list_entities` returns nothing under any status, and "archive" is not
a valid search tier, so the reason cannot be read back through the client at all.
Every archival is therefore journalled with the body it retired, or a demotion
would leave no auditable trace.

Two smaller asymmetries are unwrapped here rather than at every call site:
`get_state` nests the payload under "body", and `get_reference` returns that body
as a JSON string even though `set_reference` accepts a dict.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from sibyl_memory_client import MemoryClient
from sibyl_memory_client.exceptions import NotFoundError

# The published methodology is generated from these constants, so the
# documentation cannot drift from the engine. See brief part 20.

# Three occurrences, not two: in this dataset two is coincidence.
PROMOTION_THRESHOLD = 3

# How long an observation keeps supporting a durable fact. Past this the fact is
# archived rather than deleted, because "we stopped seeing it" is not the same
# claim as "it stopped being true", and a judge should be able to tell them apart.
DECAY_DAYS = 90

# Upper bound on a single journal scan. The free tier caps the database at
# 5,242,880 bytes, so one dossier cannot grow past this in practice.
JOURNAL_SCAN_LIMIT = 1000

BEHAVIOUR = "behaviour"
FORWARD_CURSOR = "forward-cursor"

SELF_TENANT = "cairn:self"


# What a durable fact's value may be. Narrower than Any, and it is what the
# journal can actually round-trip.
type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None


def counterparty_tenant(chain: str, address: str) -> str:
    """One isolated dossier per counterparty."""
    return f"cp:{chain}:{address.lower()}"


def reviewer_tenant(address: str) -> str:
    """One isolated dossier per reviewer. Cairn keeps a record on them too."""
    return f"rv:{address.lower()}"


def _iso(moment: datetime) -> str:
    """The SDK's timestamp shape, for example 2026-09-02T09:59:22.850Z."""
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


@dataclass(frozen=True)
class Observation:
    """One event Cairn watched happen, before it reaches the journal.

    `pattern` is the behaviour this event is an instance of. Three instances of
    one pattern promote it to a durable fact.
    """

    kind: str
    pattern: str
    source: str
    content_hash: str
    occurred_at: datetime
    body: Mapping[str, Any]
    reviewer: str | None = None

    def as_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "pattern": self.pattern,
            "source": self.source,
            "content_hash": self.content_hash,
            "occurred_at": _iso(self.occurred_at),
            "body": dict(self.body),
            "reviewer": self.reviewer,
        }


@dataclass(frozen=True)
class Promotion:
    """A pattern that crossed the threshold and became a durable fact."""

    pattern: str
    n: int
    first_seen: str
    last_seen: str
    observation_ids: tuple[str, ...]


@dataclass(frozen=True)
class Contradiction:
    """Cairn's own record disagreeing with itself. The only route to `suspect`."""

    category: str
    name: str
    old: JsonValue
    new: JsonValue
    observation_id: str


@dataclass(frozen=True)
class Archived:
    """A durable fact retired because the observations behind it aged out."""

    category: str
    name: str
    reason: str
    last_seen: str


@dataclass(frozen=True)
class Written:
    """The result of recording one observation."""

    observation_id: str
    promotion: Promotion | None


class Store(Protocol):
    """The interface every caller outside this module uses."""

    def use(self, tenant_id: str) -> AbstractContextManager[None]: ...

    def record_observation(self, obs: Observation) -> Written: ...

    def observations(self, *, pattern: str | None = None) -> list[dict[str, Any]]: ...

    def fact(self, category: str, name: str) -> dict[str, Any] | None: ...

    def assert_fact(
        self, category: str, name: str, value: JsonValue, *, observation_id: str
    ) -> Contradiction | None: ...

    def facts(self, category: str | None = None) -> list[dict[str, Any]]: ...

    def archive_stale(self, *, now: datetime | None = None) -> list[Archived]: ...

    def put_reference(self, key: str, body: Mapping[str, Any]) -> None: ...

    def reference(self, key: str) -> dict[str, Any] | None: ...

    def put_verdict(self, body: Mapping[str, Any]) -> None: ...

    def verdict(self) -> dict[str, Any] | None: ...

    def hand_forward(self, items: Sequence[Mapping[str, Any]]) -> str: ...

    def drain_forward(self) -> list[dict[str, Any]]: ...


class MemoryStore:
    """Sibyl Memory, wrapped so no other module has to know it is there."""

    def __init__(self, client: MemoryClient) -> None:
        self._m = client

    @classmethod
    def open(cls, path: str | Path) -> MemoryStore:
        """Local, offline, no credentials. Proven by scripts/verify_memory.py."""
        return cls(MemoryClient.local(path))

    def close(self) -> None:
        self._m.storage.close()

    # ---- tenancy ---------------------------------------------------------
    # A verdict about A reads A's dossier, then the dossiers of the reviewers
    # who made claims about A, then writes back to both. Three tenants
    # coordinate to produce one answer, inside one database file.

    @contextmanager
    def use(self, tenant_id: str) -> Iterator[None]:
        """Switch dossiers for the duration of the block, then switch back."""
        previous = self._m.get_tenant()
        self._m.set_tenant(tenant_id)
        try:
            yield
        finally:
            self._m.set_tenant(previous)

    # ---- COLD, the journal -----------------------------------------------

    def record_observation(self, obs: Observation) -> Written:
        """Append one observation, then promote its pattern if it is now due.

        The journal is never rewritten. Promotion adds a WARM entity beside it
        and journals the promotion as its own event, so the tier migration is
        itself part of the record.
        """
        event_id: Any = self._m.write_event(
            evaluated={"observation": obs.as_payload()},
            acted={"tier": "COLD", "wrote": "journal"},
            forward=[],
        )
        promotion = self._promote_if_due(obs)
        return Written(observation_id=str(event_id), promotion=promotion)

    def observations(self, *, pattern: str | None = None) -> list[dict[str, Any]]:
        """Every observation in this dossier, oldest first."""
        out: list[dict[str, Any]] = []
        for event in self._m.read_events(limit=JOURNAL_SCAN_LIMIT):
            payload = self._observation_of(event)
            if payload is None:
                continue
            if pattern is not None and payload.get("pattern") != pattern:
                continue
            out.append({"id": event["id"], **payload})
        out.sort(key=lambda row: str(row["occurred_at"]))
        return out

    @staticmethod
    def _observation_of(event: Mapping[str, Any]) -> dict[str, Any] | None:
        evaluated = event.get("evaluated")
        if not isinstance(evaluated, dict):
            return None
        payload = evaluated.get("observation")
        if not isinstance(payload, dict):
            return None
        return payload

    # ---- WARM, durable facts ---------------------------------------------

    def _promote_if_due(self, obs: Observation) -> Promotion | None:
        """Promote a pattern seen PROMOTION_THRESHOLD times inside the window.

        Occurrences are counted on each observation's own `occurred_at`, not on
        the journal's write timestamp, so backfilling an index cannot promote a
        pattern whose evidence is already stale.
        """
        seen = self.observations(pattern=obs.pattern)
        cutoff = obs.occurred_at.astimezone(UTC) - timedelta(days=DECAY_DAYS)
        fresh = [row for row in seen if _parse(str(row["occurred_at"])) >= cutoff]
        if len(fresh) < PROMOTION_THRESHOLD:
            return None

        first_seen = str(fresh[0]["occurred_at"])
        last_seen = str(fresh[-1]["occurred_at"])
        ids = tuple(str(row["id"]) for row in fresh)
        already = self.fact(BEHAVIOUR, obs.pattern)

        self._m.set_entity(
            BEHAVIOUR,
            obs.pattern,
            {
                "value": obs.pattern,
                "kind": obs.kind,
                "n": len(fresh),
                "first_seen": first_seen,
                "last_seen": last_seen,
                "observation_ids": list(ids),
            },
            status="active",
        )

        if already is None:
            # The promotion is an event in its own right, so a judge can match
            # this row to the moment the pattern stopped being a coincidence.
            self._m.write_event(
                evaluated={"promotion": {"pattern": obs.pattern, "n": len(fresh)}},
                acted={"tier": "WARM", "promoted": obs.pattern, "from": "COLD"},
                forward=[],
            )

        return Promotion(
            pattern=obs.pattern,
            n=len(fresh),
            first_seen=first_seen,
            last_seen=last_seen,
            observation_ids=ids,
        )

    def fact(self, category: str, name: str) -> dict[str, Any] | None:
        return self._maybe_entity(category, name)

    def _maybe_entity(self, category: str, name: str) -> dict[str, Any] | None:
        try:
            found: Any = self._m.get_entity(category, name)
        except NotFoundError:
            return None
        return found if isinstance(found, dict) else None

    def facts(self, category: str | None = None) -> list[dict[str, Any]]:
        rows: Any = self._m.list_entities(category, limit=JOURNAL_SCAN_LIMIT)
        return [row for row in rows if isinstance(row, dict)]

    def assert_fact(
        self, category: str, name: str, value: JsonValue, *, observation_id: str
    ) -> Contradiction | None:
        """Write a durable fact, journalling the disagreement if there is one.

        The schema's uniqueness on (tenant, category, name) means a contradiction
        overwrites rather than duplicating, so the entity cannot drift. Both the
        old and the new value go to the journal, so the change stays auditable
        even though the entity keeps no history of its own.
        """
        existing = self._maybe_entity(category, name)
        old = existing["body"].get("value") if existing else None
        contradiction: Contradiction | None = None

        if existing is not None and old != value:
            contradiction = Contradiction(
                category=category, name=name, old=old, new=value, observation_id=observation_id
            )

        self._m.set_entity(category, name, {"value": value}, status="active")

        if contradiction is not None:
            self._m.write_event(
                evaluated={
                    "contradiction": {
                        "category": category,
                        "name": name,
                        "old": old,
                        "new": value,
                        "observation_id": observation_id,
                    }
                },
                acted={"tier": "WARM", "overwrote": name},
                forward=[{"corroborate": name}],
            )
        return contradiction

    # ---- ARCHIVE, demotion by decay --------------------------------------

    def archive_stale(self, *, now: datetime | None = None) -> list[Archived]:
        """Retire facts whose supporting observations have all aged out.

        Archived, never deleted. The client cannot read an archived row back, so
        the body and the reason are journalled first.
        """
        moment = (now or datetime.now(UTC)).astimezone(UTC)
        cutoff = moment - timedelta(days=DECAY_DAYS)
        retired: list[Archived] = []

        for entity in self._m.list_entities(BEHAVIOUR, limit=JOURNAL_SCAN_LIMIT):
            body = entity.get("body")
            if not isinstance(body, dict):
                continue
            last_seen = body.get("last_seen")
            if not isinstance(last_seen, str) or _parse(last_seen) >= cutoff:
                continue

            reason = "evidence aged out"
            name = str(entity["name"])
            self._m.write_event(
                evaluated={"archival": {"category": BEHAVIOUR, "name": name, "body": body}},
                acted={"tier": "ARCHIVE", "archived": name, "reason": reason},
                forward=[],
            )
            self._m.archive_entity(BEHAVIOUR, name, reason=reason)
            retired.append(
                Archived(category=BEHAVIOUR, name=name, reason=reason, last_seen=last_seen)
            )
        return retired

    # ---- REFERENCE -------------------------------------------------------

    def put_reference(self, key: str, body: Mapping[str, Any]) -> None:
        self._m.set_reference(key, dict(body))

    def reference(self, key: str) -> dict[str, Any] | None:
        held = self._m.get_reference(key)
        if held is None:
            return None
        body = held.get("body")
        # set_reference takes a dict but get_reference hands the body back as a
        # JSON string, so the round trip is not symmetric.
        if isinstance(body, str):
            decoded: Any = json.loads(body)
            return decoded if isinstance(decoded, dict) else None
        return body if isinstance(body, dict) else None

    # ---- HOT, the live verdict -------------------------------------------

    def put_verdict(self, body: Mapping[str, Any]) -> None:
        """Rewritten in place. The journal keeps the history, this does not."""
        self._m.set_state("verdict", dict(body))

    def verdict(self) -> dict[str, Any] | None:
        return self._state_body("verdict")

    def _state_body(self, key: str) -> dict[str, Any] | None:
        """get_state wraps the payload as {"body": ..., "updated_at": ...}."""
        held = self._m.get_state(key)
        if not isinstance(held, dict):
            return None
        body = held.get("body")
        return body if isinstance(body, dict) else None

    # ---- the session baton -----------------------------------------------

    def hand_forward(self, items: Sequence[Mapping[str, Any]]) -> str:
        """Leave work for the next session to pick up."""
        event_id: Any = self._m.write_event(
            evaluated={"handoff": {"n": len(items)}},
            acted={"tier": "COLD", "wrote": "forward"},
            forward=[dict(item) for item in items],
        )
        return str(event_id)

    def drain_forward(self) -> list[dict[str, Any]]:
        """Cairn's first act on boot: take what the last session left behind.

        The cursor lives in HOT state, so a baton is handed over exactly once
        however many times the process restarts.
        """
        cursor = self._state_body(FORWARD_CURSOR)
        raw_since = cursor.get("ts") if cursor is not None else None
        since = raw_since if isinstance(raw_since, str) else None

        pending: list[dict[str, Any]] = []
        newest: str | None = None
        for event in self._m.read_events(since=since, limit=JOURNAL_SCAN_LIMIT):
            stamp = str(event["ts"])
            if since is not None and stamp == since:
                continue  # `since` is inclusive, so do not re-drain the cursor event
            newest = stamp if newest is None or stamp > newest else newest
            forward = event.get("forward")
            if isinstance(forward, list):
                pending.extend(item for item in forward if isinstance(item, dict))

        if newest is not None:
            self._m.set_state(FORWARD_CURSOR, {"ts": newest})
        return pending


class NullStore:
    """Cairn with its memory removed. Every read empty, every write a no-op.

    This is the other half of the deletion test. It exists so the swap is one
    line at the call site rather than a branch inside the engine.
    """

    @contextmanager
    def use(self, tenant_id: str) -> Iterator[None]:
        del tenant_id
        yield

    def record_observation(self, obs: Observation) -> Written:
        del obs
        return Written(observation_id="", promotion=None)

    def observations(self, *, pattern: str | None = None) -> list[dict[str, Any]]:
        del pattern
        return []

    def fact(self, category: str, name: str) -> dict[str, Any] | None:
        del category, name
        return None

    def assert_fact(
        self, category: str, name: str, value: JsonValue, *, observation_id: str
    ) -> Contradiction | None:
        del category, name, value, observation_id
        return None

    def facts(self, category: str | None = None) -> list[dict[str, Any]]:
        del category
        return []

    def archive_stale(self, *, now: datetime | None = None) -> list[Archived]:
        del now
        return []

    def put_reference(self, key: str, body: Mapping[str, Any]) -> None:
        del key, body

    def reference(self, key: str) -> dict[str, Any] | None:
        del key
        return None

    def put_verdict(self, body: Mapping[str, Any]) -> None:
        del body

    def verdict(self) -> dict[str, Any] | None:
        return None

    def hand_forward(self, items: Sequence[Mapping[str, Any]]) -> str:
        del items
        return ""

    def drain_forward(self) -> list[dict[str, Any]]:
        return []
