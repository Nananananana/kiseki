"""Suggestions are the owner's own evidence, pointed forward.

Two deterministic shapes, no model, no external catalogue: a place
the owner used to revisit and has not lately (visits and cadence
say so, over a span long enough to be a habit rather than a trip),
and an interest that went dormant after being seen in several
readings. Every suggestion's why is arithmetic the reader
can check, and its reference speaks the profile's own vocabulary,
so `kiseki correct` can decline a suggestion the way it declines a
reading. See ADR-0050.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique

from kiseki.domain.lifecycle import LifecycleReport, LifecycleStage
from kiseki.domain.services.place_reading import PlaceProfile

SUGGESTION_CAP = 5
OVERDUE_FACTOR = 2
MIN_VISITS = 3
HABIT_SPAN_DAYS = 30
"""How far apart the first and last visit must sit before a cadence
counts as a habit. Three days in a row on a holiday produce a
two-day median gap and a year of absence; that is a trip, and
saying "you are overdue" about it would be arithmetic pretending to
be understanding."""
MIN_SEEN = 2
CONFIDENCE_SATURATION = 6


@unique
class SuggestionKind(Enum):
    REVISIT = "revisit"
    REVIVE = "revive"
    DAY_TRIP = "day_trip"


@dataclass(frozen=True)
class Suggestion:
    """One suggestion, with the arithmetic that earned it."""

    kind: SuggestionKind
    reference: str
    confidence: float
    days_since: int | None = None
    cadence_days: int | None = None
    seen_profiles: int | None = None
    baseline: float | None = None
    distance_km: float | None = None

    def __post_init__(self) -> None:
        if not self.reference:
            raise ValueError("a suggestion needs a reference")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must lie within [0, 1]")


def _naive(moment: datetime) -> datetime:
    return moment.replace(tzinfo=None)


def derive_suggestions(
    places: Sequence[PlaceProfile],
    lifecycle: LifecycleReport | None,
    today: datetime,
) -> tuple[Suggestion, ...]:
    """The suggestions the evidence supports, the most overdue first."""
    revisits: list[tuple[float, Suggestion]] = []
    for place in places:
        if place.visits < MIN_VISITS:
            continue
        if place.median_gap_days is None or place.median_gap_days <= 0:
            continue
        if (_naive(place.last_seen) - _naive(place.first_seen)).days < HABIT_SPAN_DAYS:
            continue
        days_since = (_naive(today) - _naive(place.last_seen)).days
        if days_since <= OVERDUE_FACTOR * place.median_gap_days:
            continue
        reference = f"place:{place.centroid.latitude:.5f},{place.centroid.longitude:.5f}"
        revisits.append(
            (
                days_since / place.median_gap_days,
                Suggestion(
                    kind=SuggestionKind.REVISIT,
                    reference=reference,
                    confidence=min(1.0, place.visits / CONFIDENCE_SATURATION),
                    days_since=days_since,
                    cadence_days=place.median_gap_days,
                ),
            )
        )
    ordered = [
        suggestion
        for _ratio, suggestion in sorted(revisits, key=lambda pair: (-pair[0], pair[1].reference))
    ]

    if lifecycle is not None:
        dormant = [
            item
            for item in lifecycle.lifecycles
            if item.stage is LifecycleStage.DORMANT and item.seen_profiles >= MIN_SEEN
        ]
        for item in sorted(dormant, key=lambda entry: (-entry.baseline, entry.topic)):
            ordered.append(
                Suggestion(
                    kind=SuggestionKind.REVIVE,
                    reference=item.topic,
                    confidence=min(1.0, item.seen_profiles / CONFIDENCE_SATURATION),
                    seen_profiles=item.seen_profiles,
                    baseline=item.baseline,
                )
            )

    return tuple(ordered[:SUGGESTION_CAP])
