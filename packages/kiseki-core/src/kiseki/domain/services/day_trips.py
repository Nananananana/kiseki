"""Somewhere to go, at a distance the owner already travels.

A recommender decides how far a day trip is. This does not: it reads
the distance covered by the owner's own outings and takes the share
that describes them, so "within reach" means "you have gone this far,
and often". Nothing outside the library is consulted, and no place is
invented -- the candidates are places the owner has already been, once
or twice, and not for a long time.

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

REACH_SHARE = 0.8
"""The share of outings the usual reach must cover. Not a rule about
distance -- a description of how often the owner stays inside it."""

QUIET_DAYS = 180
"""How long a place must have gone unvisited before suggesting it
again is telling the owner something they had forgotten."""

MAX_VISITS = 2
"""More visits than this and the place has a rhythm, which `go back`
already reads. This shape is for the ones that never became one."""

DAY_TRIP_CAP = 3
CONFIDENCE_SATURATION = 6
METRES_PER_KM = 1000.0


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
    """The distances the owner covers in a day, from their own outings."""
    distances = sorted(
        outing.travelled.meters / METRES_PER_KM for outing in outings if outing.stops
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


def derive_day_trips(
    places: Sequence[PlaceProfile],
    reach: Reach,
    today: datetime,
) -> tuple[Suggestion, ...]:
    """Quiet places inside the owner's own reach, the nearest first.

    The centre is where the owner is most often: the most visited place
    of their own history, not an address anyone had to supply.
    """
    if not places:
        return ()
    centre = max(places, key=lambda place: place.visits).centroid
    candidates: list[tuple[float, Suggestion]] = []
    for place in places:
        if place.visits > MAX_VISITS:
            continue
        days_since = (_naive(today) - _naive(place.last_seen)).days
        if days_since < QUIET_DAYS:
            continue
        km = centre.distance_to(place.centroid).meters / METRES_PER_KM
        if km <= 0 or km > reach.usual_km:
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
    ordered = sorted(candidates, key=lambda pair: (pair[0], pair[1].reference))
    return tuple(suggestion for _km, suggestion in ordered[:DAY_TRIP_CAP])
