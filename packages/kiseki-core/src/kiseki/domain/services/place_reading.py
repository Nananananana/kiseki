"""What the owner's own journeys say about each place.

Stops are clustered greedily in time order: a stop joins the first
place whose running centre lies within PLACE_RADIUS, else it founds
a new place. Deterministic for a given history, derived on demand,
stored nowhere. A place profile is arithmetic only -- visits, first
and last, the median gap between revisits -- and names stay out of
the domain: the CLI resolves them at display time (ADR-0040).
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
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

    def __post_init__(self) -> None:
        if self.visits < 1:
            raise ValueError("a place needs at least one visit")
        if self.first_seen > self.last_seen:
            raise ValueError("the first visit cannot follow the last")


@dataclass
class _Cluster:
    stops: list[Stop]

    @property
    def centre(self) -> GeoPoint:
        return GeoPoint(
            sum(stop.centroid.latitude for stop in self.stops) / len(self.stops),
            sum(stop.centroid.longitude for stop in self.stops) / len(self.stops),
        )


def derive_place_profiles(outings: Sequence[Outing]) -> tuple[PlaceProfile, ...]:
    """Every place the journeys know, the most visited first."""
    ordered = sorted(
        (stop for outing in outings for stop in outing.stops),
        key=lambda stop: stop.time_range.start,
    )
    clusters: list[_Cluster] = []
    for stop in ordered:
        home = next(
            (
                cluster
                for cluster in clusters
                if cluster.centre.distance_to(stop.centroid).meters <= PLACE_RADIUS.meters
            ),
            None,
        )
        if home is None:
            clusters.append(_Cluster([stop]))
        else:
            home.stops.append(stop)

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
