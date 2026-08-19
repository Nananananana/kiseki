"""What the owner's own journeys say about each place.

Stops are clustered greedily in time order: a stop joins the first
place whose running centre lies within PLACE_RADIUS, else it founds
a new place. Deterministic for a given history, derived on demand,
stored nowhere. A place profile is arithmetic only -- visits, first
and last, the median gap between revisits -- and names stay out of
the domain: the CLI resolves them at display time (ADR-0040).

A place also knows how many of its visits happened on a trip. Without
that, an airport visited on the way to every holiday looks like a
habit: eight visits, spread over two years, a tidy cadence, and
nothing about it is somewhere the owner chooses to go. See ADR-0060.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import datetime
from statistics import median

from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.shared.geo import Distance, GeoPoint

PLACE_RADIUS = Distance(150)


@dataclass(frozen=True)
class PlaceProfile:
    """One place, in the owner's own numbers."""

    centroid: GeoPoint
    visits: int
    first_seen: datetime
    last_seen: datetime
    median_gap_days: int | None
    trip_visits: int = 0

    def __post_init__(self) -> None:
        if self.visits < 1:
            raise ValueError("a place needs at least one visit")
        if self.first_seen > self.last_seen:
            raise ValueError("the first visit cannot follow the last")
        if not 0 <= self.trip_visits <= self.visits:
            raise ValueError("trip visits are some of the visits, or all of them")

    @property
    def only_on_trips(self) -> bool:
        """Every visit happened while the owner was away from home."""
        return self.trip_visits == self.visits


@dataclass
class _Cluster:
    stops: list[Stop]
    on_trip: list[bool]

    @property
    def centre(self) -> GeoPoint:
        return GeoPoint(
            sum(stop.centroid.latitude for stop in self.stops) / len(self.stops),
            sum(stop.centroid.longitude for stop in self.stops) / len(self.stops),
        )


def derive_place_profiles(
    outings: Sequence[Outing],
    trip_outings: AbstractSet[str] = frozenset(),
) -> tuple[PlaceProfile, ...]:
    """Every place the journeys know, the most visited first."""
    marked = sorted(
        ((stop, outing.id.value in trip_outings) for outing in outings for stop in outing.stops),
        key=lambda pair: pair[0].time_range.start,
    )
    clusters: list[_Cluster] = []
    for stop, on_trip in marked:
        home = next(
            (
                cluster
                for cluster in clusters
                if cluster.centre.distance_to(stop.centroid).meters <= PLACE_RADIUS.meters
            ),
            None,
        )
        if home is None:
            clusters.append(_Cluster([stop], [on_trip]))
        else:
            home.stops.append(stop)
            home.on_trip.append(on_trip)

    profiles: list[PlaceProfile] = []
    for cluster in clusters:
        starts = [stop.time_range.start for stop in cluster.stops]
        gaps = [(later - earlier).days for earlier, later in itertools.pairwise(starts)]
        profiles.append(
            PlaceProfile(
                centroid=cluster.centre,
                visits=len(cluster.stops),
                first_seen=starts[0],
                last_seen=starts[-1],
                median_gap_days=round(median(gaps)) if gaps else None,
                trip_visits=sum(cluster.on_trip),
            )
        )
    return tuple(
        sorted(
            profiles,
            key=lambda place: (
                -place.visits,
                place.centroid.latitude,
                place.centroid.longitude,
            ),
        )
    )
