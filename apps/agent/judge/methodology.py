"""The public scoring methodology, generated from the engine's own constants.

Nothing here restates a number. Every value is imported from the module that
uses it, so the published methodology cannot drift from the code that decides.
"""

from __future__ import annotations

from typing import Any

from apps.agent.memory.store import DECAY_DAYS, PROMOTION_THRESHOLD

from .verdict import (
    CONFIDENCE_FULL_SOURCES,
    CONTRADICTION_PENALTY,
    GROUNDED_MIN_CORROBORATED,
    NEUTRAL_REVIEWER_WEIGHT,
    PROVISIONAL_BELOW,
    W_CORROBORATION,
    W_RECENCY,
    W_VOLUME,
)


def published() -> dict[str, Any]:
    """Everything a reader needs to reproduce a verdict by hand."""
    return {
        "memory": {
            "promotion_threshold": PROMOTION_THRESHOLD,
            "decay_days": DECAY_DAYS,
        },
        "standing": {
            "grounded": (
                f"{GROUNDED_MIN_CORROBORATED} or more corroborated observations, "
                "and nothing in the record contradicting itself"
            ),
            "suspect": (
                "the record contradicts itself, and the contradicting "
                "observations can be named"
            ),
            "thin": f"fewer than {GROUNDED_MIN_CORROBORATED} corroborated observations",
            "dormant": f"nothing witnessed for {DECAY_DAYS} days",
        },
        "confidence": {
            "formula": (
                "clamp(W_VOLUME * min(distinct_sources / CONFIDENCE_FULL_SOURCES, 1) "
                "+ W_CORROBORATION * (corroborated / n) "
                "+ W_RECENCY * max(0, 1 - age_days / DECAY_DAYS) "
                "- CONTRADICTION_PENALTY * contradictions)"
            ),
            "w_volume": W_VOLUME,
            "w_corroboration": W_CORROBORATION,
            "w_recency": W_RECENCY,
            "confidence_full_sources": CONFIDENCE_FULL_SOURCES,
            "volume_counts": (
                "distinct sources, not observations: one claimant speaking a "
                "hundred times is one source"
            ),
            "contradiction_penalty": CONTRADICTION_PENALTY,
            "null_means": "no record at all, which is not the same as a confidence of 0.0",
        },
        "reviewer_weight": {
            "corroborated": "another claimant left a record about the same agent",
            "neutral_weight": NEUTRAL_REVIEWER_WEIGHT,
            "provisional_below": PROVISIONAL_BELOW,
            "provisional_means": (
                "too short a record to judge, so the claimant carries the neutral "
                "weight and the weight is returned flagged"
            ),
        },
    }
