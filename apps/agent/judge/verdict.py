"""The verdict engine. Arithmetic over the record, never a model call.

A verdict is what Cairn currently believes about one counterparty, carrying a
confidence and a basis: the specific observations the judgment rests on. Nothing
in this module calls an LLM. The rationale sentence rendered elsewhere is
presentation; the decision here is deterministic, and running it twice over the
same record returns the same answer.

The shape of the reasoning, from brief part 10:

    1. load the prior from HOT state, cold-starting from WARM entities if absent
    2. pull the observations from COLD, weighted by recency and reviewer weight
    3. compute standing
    4. compute confidence from count, corroboration rate and recency
    5. write the verdict back to HOT and journal the evaluation
    6. return the verdict with the observation ids it used

Two rules from part 21 are enforced here rather than left to callers.

Absence is never evidence. A source that was not ingested makes its checks skip,
and the counterparty stays `thin`. Only a source that was ingested and disagrees
with the record can produce `suspect`.

`suspect` requires a pointable contradiction. The engine may only return it when
it can name the observations that disagree. Reaching `suspect` with an empty
basis raises rather than downgrading quietly, because an auditor that accuses
without being able to say why is worse than one that stays silent.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from apps.agent.memory.store import (
    DECAY_DAYS,
    Store,
    counterparty_tenant,
    reviewer_tenant,
)

Standing = Literal["grounded", "thin", "suspect", "dormant"]

# ---- the published methodology ------------------------------------------
# These constants are the methodology. apps/agent/judge/methodology.py exports
# them so the documentation is generated from the engine and cannot drift.

#: Corroborated observations needed before a counterparty can be `grounded`.
GROUNDED_MIN_CORROBORATED = 3

#: Distinct independent sources at which the volume term saturates.
#:
#: Volume counts sources, not observations. Raw observation count is the
#: cheapest quantity on this chain to manufacture, a median of $0.0027 to move,
#: and the busiest dossier in the indexed set is 100 pieces of feedback from a
#: single claimant. Scoring that as high confidence would reward exactly the
#: behaviour Cairn exists to catch.
CONFIDENCE_FULL_SOURCES = 5

#: Confidence weights. They sum to 1 before any penalty is applied.
W_VOLUME = 0.40
W_CORROBORATION = 0.35
W_RECENCY = 0.25

#: Subtracted from confidence for each unresolved contradiction.
CONTRADICTION_PENALTY = 0.25

#: A reviewer whose record is too short to judge carries this weight.
NEUTRAL_REVIEWER_WEIGHT = 0.5

#: Corroborated outcomes a reviewer needs before their weight stops being
#: provisional. Below this the API returns the weight flagged.
PROVISIONAL_BELOW = 3

_REGISTRATION = "erc8004_registration"
_FEEDBACK = "erc8004_feedback"
_CLAIM = "erc8004_claim"


class EmptyBasisError(RuntimeError):
    """Raised if a code path reaches `suspect` without naming an observation.

    Part 21 makes this a bug rather than a silent downgrade: Cairn publishes
    judgments about real, named third parties, and an accusation it cannot
    point at is the one mistake that outlives the hackathon.
    """


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class BasisItem:
    """One observation the verdict rests on."""

    observation_id: str
    kind: str
    occurred_at: str
    content_hash: str
    source: str
    reviewer: str | None
    corroborated: bool
    weight: float

    def as_payload(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "kind": self.kind,
            "occurred_at": self.occurred_at,
            "content_hash": self.content_hash,
            "source": self.source,
            "reviewer": self.reviewer,
            "corroborated": self.corroborated,
            "weight": round(self.weight, 4),
        }


@dataclass(frozen=True)
class ContradictionRef:
    """Two things the record says that cannot both be true.

    `observation_ids` is what makes a `suspect` standing pointable. It is never
    empty: the engine raises instead of producing one that is.
    """

    claim: str
    detail: str
    observation_ids: tuple[str, ...]

    def as_payload(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "detail": self.detail,
            "observation_ids": list(self.observation_ids),
        }


@dataclass(frozen=True)
class ReviewerWeight:
    """How much a claimant's word moves a verdict, and whether we can tell yet."""

    address: str
    claims: int
    corroborated: int
    weight: float
    provisional: bool

    def as_payload(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "claims": self.claims,
            "corroborated": self.corroborated,
            "weight": round(self.weight, 4),
            "provisional": self.provisional,
        }


@dataclass(frozen=True)
class Verdict:
    """Cairn's current judgment about one counterparty."""

    counterparty: str
    standing: Standing
    confidence: float | None
    basis: tuple[BasisItem, ...]
    contradictions: tuple[ContradictionRef, ...] = ()
    reviewers: tuple[ReviewerWeight, ...] = ()
    prior: dict[str, Any] | None = None
    sources_unavailable: tuple[str, ...] = ()
    evaluated_at: str = ""

    @property
    def no_basis(self) -> bool:
        """True when the engine had nothing to reason over."""
        return not self.basis

    def as_payload(self) -> dict[str, Any]:
        return {
            "counterparty": self.counterparty,
            "standing": self.standing,
            "confidence": self.confidence,
            "basis": [item.as_payload() for item in self.basis],
            "contradictions": [c.as_payload() for c in self.contradictions],
            "reviewers": [r.as_payload() for r in self.reviewers],
            "sources_unavailable": list(self.sources_unavailable),
            "no_basis": self.no_basis,
            "evaluated_at": self.evaluated_at,
        }


@dataclass
class _Tally:
    """Working totals while walking one dossier."""

    items: list[BasisItem] = field(default_factory=list)
    corroborated: int = 0
    unavailable: set[str] = field(default_factory=set)
    #: Distinct parties behind the record. A claimant address, or "chain" for
    #: something Cairn read from the registry itself rather than from anyone.
    sources: set[str] = field(default_factory=set)


def _recency(occurred_at: str, now: datetime) -> float:
    """1.0 for an observation witnessed now, 0.0 at the edge of the window."""
    age_days = (now - _parse(occurred_at)).total_seconds() / 86400.0
    return _clamp(1.0 - age_days / DECAY_DAYS)


def reviewer_weight(
    store: Store,
    address: str,
    *,
    witnessed: Mapping[Any, set[str]] | None = None,
) -> ReviewerWeight:
    """Weight a claimant by whether their claims were independently witnessed.

    This is the layer ERC-8004 names as missing. The claimant's own dossier
    holds every claim they have made, which is the denominator. A claim counts
    as corroborated when some other claimant left a record about the same agent,
    so a reviewer cannot corroborate themselves.

    `witnessed` maps agent id to the set of claimants seen for that agent, taken
    from the dossier under evaluation. Corroboration is therefore only counted
    over agents currently in view: Cairn does not hold a global agent index, and
    inventing one to raise a reviewer's weight would be exactly the kind of
    unbacked number this project exists to replace. Anything below
    PROVISIONAL_BELOW corroborated outcomes carries the neutral weight and is
    returned flagged, so a short record neither helps nor harms the reviewer.
    """
    seen = witnessed or {}

    with store.use(reviewer_tenant(address)):
        claims = [row for row in store.observations() if row.get("kind") == _CLAIM]

    corroborated = 0
    for claim in claims:
        body = claim.get("body")
        if not isinstance(body, dict):
            continue
        agent_id = body.get("agent_id")
        claimant = str(body.get("client", "")).lower()
        if agent_id is None:
            continue
        others = seen.get(agent_id, set()) - {claimant}
        if others:
            corroborated += 1

    provisional = corroborated < PROVISIONAL_BELOW
    if provisional or not claims:
        weight = NEUTRAL_REVIEWER_WEIGHT
    else:
        weight = _clamp(corroborated / len(claims))

    return ReviewerWeight(
        address=address.lower(),
        claims=len(claims),
        corroborated=corroborated,
        weight=weight,
        provisional=provisional,
    )


def _contradictions(observations: Sequence[Mapping[str, Any]]) -> list[ContradictionRef]:
    """Find what the record itself disagrees about.

    One agent id registered to two different owners is a disagreement Cairn can
    point at: both observations are chain-witnessed, both are in the journal,
    and they cannot both describe the present. Nothing here infers intent, and
    a source that was never fetched contributes nothing.
    """
    owners: dict[Any, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for row in observations:
        if row.get("kind") != _REGISTRATION:
            continue
        body = row.get("body")
        if not isinstance(body, dict):
            continue
        agent_id = body.get("agent_id")
        owner = body.get("owner")
        if agent_id is None or not isinstance(owner, str):
            continue
        owners[agent_id][owner.lower()].append(str(row.get("id", "")))

    found: list[ContradictionRef] = []
    for agent_id, by_owner in owners.items():
        if len(by_owner) < 2:
            continue
        ids: list[str] = []
        for id_list in by_owner.values():
            ids.extend(i for i in id_list if i)
        if not ids:
            # Without observation ids the disagreement is not pointable, so it
            # is not a contradiction we are willing to publish.
            continue
        found.append(
            ContradictionRef(
                claim=f"agent {agent_id} owner",
                detail="the registry recorded two different owners for one agent id",
                observation_ids=tuple(sorted(ids)),
            )
        )
    return found


def _weigh(
    store: Store,
    observations: Sequence[Mapping[str, Any]],
    now: datetime,
) -> tuple[_Tally, dict[str, ReviewerWeight]]:
    """Score each observation by recency and by who surfaced it."""
    tally = _Tally()
    weights: dict[str, ReviewerWeight] = {}

    claimants: set[str] = set()
    for row in observations:
        reviewer = row.get("reviewer")
        if isinstance(reviewer, str) and reviewer:
            claimants.add(reviewer.lower())

    # Corroboration is a distinct-claimant question, so it is decided over the
    # whole dossier before any single observation is scored.
    per_claimant: dict[Any, set[str]] = defaultdict(set)
    for row in observations:
        claim_body = row.get("body")
        if not isinstance(claim_body, dict):
            continue
        subject = claim_body.get("agent_id")
        client = claim_body.get("client")
        if subject is not None and isinstance(client, str):
            per_claimant[subject].add(client.lower())

    for address in sorted(claimants):
        weights[address] = reviewer_weight(store, address, witnessed=per_claimant)

    for row in observations:
        occurred_at = str(row.get("occurred_at", ""))
        if not occurred_at:
            continue
        raw_body = row.get("body")
        body: dict[str, Any] = raw_body if isinstance(raw_body, dict) else {}

        # Absence is never evidence: a registration file we could not fetch
        # makes that source unavailable, it does not make a claim.
        if row.get("kind") == _REGISTRATION and body.get("registration_available") is False:
            tally.unavailable.add("erc8004 registration file")

        reviewer = row.get("reviewer")
        reviewer_key = reviewer.lower() if isinstance(reviewer, str) and reviewer else None
        factor = weights[reviewer_key].weight if reviewer_key in weights else 1.0

        subject = body.get("agent_id")
        corroborated = len(per_claimant.get(subject, set())) >= 2

        item = BasisItem(
            observation_id=str(row.get("id", "")),
            kind=str(row.get("kind", "")),
            occurred_at=occurred_at,
            content_hash=str(row.get("content_hash", "")),
            source=str(row.get("source", "")),
            reviewer=reviewer_key,
            corroborated=corroborated,
            weight=_recency(occurred_at, now) * factor,
        )
        tally.items.append(item)
        tally.sources.add(reviewer_key or "chain")
        if corroborated:
            tally.corroborated += 1

    return tally, weights


def confidence_for(
    *,
    n_observations: int,
    distinct_sources: int,
    corroborated: int,
    recency: float,
    contradictions: int,
) -> float | None:
    """The published confidence formula.

        volume    = min(distinct_sources / CONFIDENCE_FULL_SOURCES, 1)
        corrob    = corroborated / n_observations
        recency   = 1 - age_of_newest / DECAY_DAYS, floored at 0

        confidence = clamp(
            W_VOLUME * volume + W_CORROBORATION * corrob + W_RECENCY * recency
            - CONTRADICTION_PENALTY * contradictions
        )

    Volume counts distinct sources rather than observations on purpose. One
    claimant speaking a hundred times is one source, and pricing it as a hundred
    would make confidence purchasable.

    Returns None when there is nothing to be confident about. A confidence of
    0.0 means Cairn looked and found the record worthless; None means there was
    no record, and the two must not render the same.
    """
    if n_observations <= 0:
        return None
    volume = _clamp(distinct_sources / CONFIDENCE_FULL_SOURCES)
    corrob = _clamp(corroborated / n_observations)
    score = W_VOLUME * volume + W_CORROBORATION * corrob + W_RECENCY * _clamp(recency)
    score -= CONTRADICTION_PENALTY * contradictions
    return round(_clamp(score), 2)


def _standing(
    *,
    n_observations: int,
    corroborated: int,
    contradictions: Sequence[ContradictionRef],
    newest: str | None,
    now: datetime,
) -> Standing:
    """The standing rules, in precedence order."""
    if n_observations == 0:
        # Nothing witnessed. Not suspicion, not staleness, just no record.
        return "thin"
    if contradictions:
        return "suspect"
    if newest is not None and _parse(newest) < now - timedelta(days=DECAY_DAYS):
        return "dormant"
    if corroborated >= GROUNDED_MIN_CORROBORATED:
        return "grounded"
    return "thin"


def evaluate(
    store: Store,
    chain: str,
    address: str,
    *,
    now: datetime | None = None,
    write: bool = True,
) -> Verdict:
    """Judge one counterparty from what Cairn has witnessed.

    Reads the counterparty's dossier, then the dossier of every claimant who has
    spoken about them, then writes back to the counterparty's. Three tenants
    coordinate to produce one answer inside a single database file.

    `write=False` evaluates without recording, which is what the deletion test
    needs so that proving the point does not itself change the record.
    """
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    tenant = counterparty_tenant(chain, address)

    with store.use(tenant):
        prior = store.verdict()
        observations = store.observations()

        if not observations:
            # Cold start: a dossier with no journal may still hold promoted
            # facts from an earlier session.
            promoted = store.facts()
            if promoted:
                prior = prior or {"from": "warm-entities", "n": len(promoted)}

        tally, weights = _weigh(store, observations, moment)
        contradictions = _contradictions(observations)

        newest = max((item.occurred_at for item in tally.items), default=None)
        recency = _recency(newest, moment) if newest else 0.0

        standing = _standing(
            n_observations=len(tally.items),
            corroborated=tally.corroborated,
            contradictions=contradictions,
            newest=newest,
            now=moment,
        )

        if standing == "suspect" and not any(c.observation_ids for c in contradictions):
            raise EmptyBasisError(
                f"refusing to publish `suspect` for {tenant} without a pointable contradiction"
            )

        confidence = confidence_for(
            n_observations=len(tally.items),
            distinct_sources=len(tally.sources),
            corroborated=tally.corroborated,
            recency=recency,
            contradictions=len(contradictions),
        )

        verdict = Verdict(
            counterparty=tenant,
            standing=standing,
            confidence=confidence,
            basis=tuple(tally.items),
            contradictions=tuple(contradictions),
            reviewers=tuple(weights[a] for a in sorted(weights)),
            prior=prior,
            sources_unavailable=tuple(sorted(tally.unavailable)),
            evaluated_at=_iso(moment),
        )

        if write:
            _record(store, verdict)

    return verdict


def _unchanged(verdict: Verdict) -> bool:
    """True when this verdict says exactly what the prior one already said."""
    prior = verdict.prior
    if not isinstance(prior, dict):
        return False
    return (
        prior.get("standing") == verdict.standing
        and prior.get("confidence") == verdict.confidence
        and len(prior.get("basis") or []) == len(verdict.basis)
    )


def _record(store: Store, verdict: Verdict) -> None:
    """Write the verdict to HOT and hand the next session what changed.

    HOT is rewritten in place, so re-evaluating costs nothing there. The baton
    is different: it is a journal event, and the journal is append-only. Handing
    the same work forward on every sweep would grow COLD without bound and, on
    the free tier, walk the database into its 5,242,880 byte cap for no new
    information. The baton carries news, so an unchanged verdict hands nothing.
    """
    store.put_verdict(verdict.as_payload())

    if _unchanged(verdict):
        return

    forward: list[dict[str, Any]] = []
    for contradiction in verdict.contradictions:
        forward.append({"corroborate": contradiction.claim})
    for reviewer in verdict.reviewers:
        if reviewer.provisional:
            forward.append({"reviewer_weight_provisional": reviewer.address})
    if verdict.standing in ("thin", "dormant"):
        forward.append({"recheck": verdict.counterparty})

    if forward:
        store.hand_forward(forward)
