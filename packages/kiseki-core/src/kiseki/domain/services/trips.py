"""A night away is one journey, not three days of them.

Outings split on silence, and sleep is silence: three days in Seoul
arrive as three separate outings, and every derivation downstream reads
them as three visits to a place the owner keeps returning to. Two
calibrations already exist to keep that misreading out of the cadence
(ADR-0050) and out of the bases a day trip is measured from (ADR-0055).
They are patches on a shape the library did not have.

A trip is that shape: a run of outings that stayed away from every place
the owner sets out from, close enough together in time to be one going,
and spanning at least one night. Outings are untouched -- a trip is
derived on top of them, the way interests are derived on top of
readings. See ADR-0060.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from kiseki.domain.outing.outing import Outing
from kiseki.domain.shared.geo import GeoPoint

AWAY_KM = 50.0
"""How far from every regular place an outing must sit before it counts
as away. Nearer than this is an errand, however late it runs."""

TRIP_GAP = timedelta(hours=36)
"""How long a silence may last inside one trip. Sleep, a morning in a
hotel and a slow start are one going; three days at home between two
weekends are not."""

METRES_PER_KM = 1000.0


@dataclass(frozen=True)
class Trip:
    """Outings that were one going, away and overnight."""

    outings: tuple[Outing, ...]
    farthest_km: float

    def __post_init__(self) -> None:
        if not self.outings:
            raise ValueError("a trip needs at least one outing")
        if self.nights < 1:
            raise ValueError("a trip spans at least one night")

    @property
    def start(self) -> datetime:
        return self.outings[0].time_range.start

    @property
    def end(self) -> datetime:
        return self.outings[-1].time_range.end

    @property
    def nights(self) -> int:
        return (self.end.date() - self.start.date()).days

    @property
    def stop_count(self) -> int:
        return sum(outing.stop_count for outing in self.outings)

    @property
    def photograph_count(self) -> int:
        return sum(outing.photograph_count for outing in self.outings)


def _distance_km(point: GeoPoint, origins: Sequence[GeoPoint]) -> float:
    return min(origin.distance_to(point).meters / METRES_PER_KM for origin in origins)


def _away_by(outing: Outing, origins: Sequence[GeoPoint]) -> float | None:
    """How far the outing went, or None if any of it was close to home."""
    distances = [_distance_km(stop.centroid, origins) for stop in outing.stops]
    if min(distances) < AWAY_KM:
        return None
    return max(distances)


def derive_trips(
    outings: Sequence[Outing],
    origins: Sequence[GeoPoint],
) -> tuple[Trip, ...]:
    """Every run of outings that was one going, away and overnight."""
    if not origins:
        return ()
    ordered = sorted(outings, key=lambda outing: outing.time_range.start)
    runs: list[list[tuple[Outing, float]]] = []
    current: list[tuple[Outing, float]] | None = None
    for outing in ordered:
        distance = _away_by(outing, origins)
        if distance is None:
            current = None
            continue
        if current is not None:
            silence = outing.time_range.start - current[-1][0].time_range.end
            if silence > TRIP_GAP:
                current = None
        if current is None:
            current = []
            runs.append(current)
        current.append((outing, distance))

    trips: list[Trip] = []
    for run in runs:
        members = tuple(outing for outing, _distance in run)
        span = members[-1].time_range.end.date() - members[0].time_range.start.date()
        if span.days < 1:
            continue
        trips.append(
            Trip(
                outings=members,
                farthest_km=max(distance for _outing, distance in run),
            )
        )
    return tuple(trips)
