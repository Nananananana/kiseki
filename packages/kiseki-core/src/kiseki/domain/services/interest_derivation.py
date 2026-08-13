"""Reads the return pattern as a set of interests.

Going back is the clearest statement of having liked somewhere, so
this service derives interests from places visited on more than one
day. It deliberately reads the return pattern rather than the anchors:
anchors include the places a life is anchored to, and an interest in
one's own home is not a finding. For the same reason, places that sit
inside an anchor's own area are left out -- they are the same
circumstances, seen through the outings. See ADR-0017.

Everything here is deterministic. No model is consulted; the numbers
come from counting, and the tests pin them exactly.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time

from kiseki.domain.analytics.analytics import PlacePreference, PlaceVisits
from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)

SCORE_HALF_VISITS = 1
"""Visit days at which the score reaches one half. Two visit days,
the minimum for an interest, already score two thirds: returning once
is most of the statement, and further returns saturate towards one."""

CONFIDENCE_HALF_VISITS = 3
"""Visit days at which the visit factor of confidence reaches one
half. Slower than the score deliberately: how strongly the evidence
points somewhere and how far it can be trusted are different rates."""

CONFIDENCE_HALF_SPAN_DAYS = 30
"""Days between first and last visit at which the span factor of
confidence reaches one half. A pattern squeezed into one week may be
a phase; the same visits spread over a year are a habit."""


def derive_interests(
    places: PlacePreference,
    generated_at: datetime,
    anchors: Sequence[Anchor] = (),
) -> Profile:
    """Read every returned-to place as an interest.

    Places seen on a single day are excluded: a single visit is not
    yet a return pattern, and single photographs are a separate source
    of evidence that arrives with captioning (FR-507). Places inside
    an anchor's area are excluded too: frequent presence around home
    or work is circumstance, not choice. The given ranking is kept;
    the measures already ordered the places, and interpretation must
    not quietly reorder what was measured.
    """
    interests = tuple(
        _interest_from(place)
        for place in places.places
        if place.was_returned_to and not _anchored(place, anchors)
    )
    return Profile(generated_at=generated_at, interests=interests)


def _anchored(place: PlaceVisits, anchors: Sequence[Anchor]) -> bool:
    """Whether the place sits inside any anchor's own area."""
    return any(
        place.centre.distance_to(anchor.area.center) <= anchor.area.radius for anchor in anchors
    )


def _interest_from(place: PlaceVisits) -> Interest:
    topic = _reference(place)
    first_seen = _midnight(place.first_visit)
    last_seen = _midnight(place.last_visit)

    # A returned-to place has distinct first and last visit days, so
    # the two ends of the pattern are always two pieces of evidence.
    evidence = (
        InterestEvidence(kind=EvidenceKind.VISIT, reference=topic, observed_at=first_seen),
        InterestEvidence(kind=EvidenceKind.VISIT, reference=topic, observed_at=last_seen),
    )

    return Interest(
        topic=topic,
        score=_score(place),
        confidence=_confidence(place),
        evidence=evidence,
        first_seen=first_seen,
        last_seen=last_seen,
    )


def _score(place: PlaceVisits) -> float:
    """How strongly the pattern points at the place, in [0, 1)."""
    return place.visit_days / (place.visit_days + SCORE_HALF_VISITS)


def _confidence(place: PlaceVisits) -> float:
    """How far the pattern can be trusted, in [0, 1).

    The product of two saturating factors: enough distinct days, and
    enough time between the first and the last of them. Twelve visits
    over two years earn a high confidence; two visits last week earn
    the same score a much lower one.
    """
    span_days = (place.last_visit - place.first_visit).days
    visits = place.visit_days / (place.visit_days + CONFIDENCE_HALF_VISITS)
    span = span_days / (span_days + CONFIDENCE_HALF_SPAN_DAYS)
    return visits * span


def _reference(place: PlaceVisits) -> str:
    """Name the place by where it is, not by what it might be.

    Five decimal places is roughly metre precision. The reference
    stays inside the library; exports and visualisation blur
    coordinates by default, and that includes these.
    """
    return f"place:{place.centre.latitude:.5f},{place.centre.longitude:.5f}"


def _midnight(day: date) -> datetime:
    return datetime.combine(day, time.min)
