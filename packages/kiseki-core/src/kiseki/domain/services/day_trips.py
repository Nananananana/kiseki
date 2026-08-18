"""Somewhere to go, at a distance the owner already travels.

A recommender decides how far a day trip is. This does not: it reads
the distance covered by the owner's own outings and takes the share
that describes them, so "within reach" means "you have gone this far,
and often". Nothing outside the library is consulted, and no place is
invented -- the candidates are places the owner has already been, once
or twice, and not for a long time.

Distance is measured from whichever of the owner's regular places is
nearest, not from one chosen centre. A life has more than one place it
returns to -- a home and a station, a home and an office -- and asking
"how far is this from the single most visited spot" gives the wrong
answer for everything anchored to the others.

A place with a rhythm is not offered here. That is what `go back` is
for (ADR-0050); this is for the ones that never became a habit and
deserved to. See ADR-0055.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.outing.outing import Outing
from kiseki.domain.services.place_reading import PlaceProfile
from kiseki.domain.services.suggesting import Suggestion, SuggestionKind
from kiseki.domain.shared.geo import GeoPoint

REACH_SHARE = 0.8
"""The share of outings the usual reach must cover. Not a rule about
distance -- a description of how often the owner stays inside it."""

QUIET_DAYS = 180
"""How long a place must have gone unvisited before suggesting it
again is telling the owner something they had forgotten."""

MAX_VISITS = 2
"""More visits than this and the place has a rhythm, which `go back`
already reads. This shape is for the ones that never became one."""

REGULAR_VISITS = 3
"""Visits enough for a place to count as one the owner comes from."""

REGULAR_SPAN_DAYS = 30
"""And spread over long enough to be a life rather than a holiday.
Three nights in one town abroad is three visits; it is not somewhere
the owner sets out from, and treating it as one put a distant island
six hundred metres from itself. The same distinction `go back` makes
between a cadence and a trip (ADR-0050)."""

MIN_TRIP_KM = 1.0
"""Nearer than this is not a day trip; it is the next street."""

DAY_TRIP_CAP = 3

NEIGHBOUR_KM = 2.0
"""Two place suggestions closer together than this are the same outing
to the same part of town. Only the first is offered: three lines naming
one neighbourhood is a list, not a suggestion. The rule is applied once,
to every place suggestion there is -- a `go back` and a `day trip` to
the same street are the same repetition to a reader."""
CONFIDENCE_SATURATION = 6
METRES_PER_KM = 1000.0
PLACE_PREFIX = "place:"


@dataclass(frozen=True)
class Reach:
    """How far the owner's own outings go."""

    outings: int
    typical_km: float
    usual_km: float
    share: float

    def __post_init__(self) -> None:
        if self.outings < 1:
            raise ValueError("a reach needs at least one outing")
        if self.usual_km < self.typical_km:
            raise ValueError("the usual reach cannot fall short of the typical one")


def _quantile(ordered: Sequence[float], share: float) -> float:
    index = min(len(ordered) - 1, round(share * (len(ordered) - 1)))
    return ordered[index]


def derive_reach(outings: Sequence[Outing]) -> Reach | None:
    """The distances the owner covers on a day they go somewhere.

    Outings with a single stop are left out: a day spent in one place
    says nothing about how far the owner travels, and counting it as
    zero drags the reach down until nothing is ever within it.
    """
    distances = sorted(
        outing.travelled.meters / METRES_PER_KM for outing in outings if len(outing.stops) > 1
    )
    if not distances:
        return None
    return Reach(
        outings=len(distances),
        typical_km=_quantile(distances, 0.5),
        usual_km=_quantile(distances, REACH_SHARE),
        share=REACH_SHARE,
    )


def _naive(moment: datetime) -> datetime:
    return moment.replace(tzinfo=None)


def _regular(places: Sequence[PlaceProfile]) -> tuple[GeoPoint, ...]:
    """The places the owner sets out from: every one they return to.

    Falls back to the most visited place when nothing qualifies, so a
    thin library still measures against something the owner knows.
    """
    regular = [
        place.centroid
        for place in places
        if place.visits >= REGULAR_VISITS
        and (_naive(place.last_seen) - _naive(place.first_seen)).days >= REGULAR_SPAN_DAYS
    ]
    if regular:
        return tuple(regular)
    busiest = max(places, key=lambda place: place.visits)
    return (busiest.centroid,)


def derive_day_trips(
    places: Sequence[PlaceProfile],
    reach: Reach,
    today: datetime,
) -> tuple[Suggestion, ...]:
    """Quiet places inside the owner's own reach, the longest gone first.

    Ordering by distance filled the list with the next street over:
    everything within walking distance is inside any reach, so the
    nearest three always won and nothing was ever discovered. What
    makes a suggestion worth reading is how long it has been, and the
    reach already decided what counts as too far.
    """
    if not places:
        return ()
    origins = _regular(places)
    candidates: list[tuple[float, Suggestion]] = []
    for place in places:
        if place.visits > MAX_VISITS:
            continue
        days_since = (_naive(today) - _naive(place.last_seen)).days
        if days_since < QUIET_DAYS:
            continue
        km = min(origin.distance_to(place.centroid).meters / METRES_PER_KM for origin in origins)
        if km < MIN_TRIP_KM or km > reach.usual_km:
            continue
        reference = f"place:{place.centroid.latitude:.5f},{place.centroid.longitude:.5f}"
        candidates.append(
            (
                km,
                Suggestion(
                    kind=SuggestionKind.DAY_TRIP,
                    reference=reference,
                    confidence=min(1.0, place.visits / CONFIDENCE_SATURATION),
                    days_since=days_since,
                    distance_km=km,
                ),
            )
        )
    ordered = sorted(
        candidates,
        key=lambda pair: (-(pair[1].days_since or 0), pair[0], pair[1].reference),
    )
    return spread_out([suggestion for _km, suggestion in ordered])[:DAY_TRIP_CAP]


def spread_out(suggestions: Sequence[Suggestion]) -> tuple[Suggestion, ...]:
    """The same suggestions, one per part of town, order preserved.

    Suggestions about topics rather than places pass through untouched:
    the rule is about a reader seeing one neighbourhood three times, and
    a topic has no neighbourhood.
    """
    kept: list[Suggestion] = []
    points: list[GeoPoint] = []
    for suggestion in suggestions:
        point = _point_of(suggestion)
        if point is None:
            kept.append(suggestion)
            continue
        if any(other.distance_to(point).meters / METRES_PER_KM < NEIGHBOUR_KM for other in points):
            continue
        kept.append(suggestion)
        points.append(point)
    return tuple(kept)


def _point_of(suggestion: Suggestion) -> GeoPoint | None:
    """The coordinate a place suggestion names, or None for a topic."""
    if not suggestion.reference.startswith(PLACE_PREFIX):
        return None
    try:
        latitude, longitude = suggestion.reference.removeprefix(PLACE_PREFIX).split(",")
        return GeoPoint(float(latitude), float(longitude))
    except ValueError:
        return None
