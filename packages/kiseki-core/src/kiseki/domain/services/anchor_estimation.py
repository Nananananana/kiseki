"""Finding the places a person photographs again and again.

The service reports what was observed at each place and stops there. It does not
decide which one is home. That decision depends on how somebody lives, and the
shares reported here let a reader, or a language model in v0.2, work it out from
evidence instead of from an assumption baked into this file.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.outing.stop import Stop
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.settings import AnchorSettings
from kiseki.domain.shared.time_range import TimeRange

WEEKEND = (5, 6)
CONFIDENCE_SATURATES_AT = 4
"""Visits beyond min_visits times this add no further confidence."""


def _within(hour: int, window: tuple[int, int]) -> bool:
    """Whether an hour falls in a window, which may wrap past midnight."""
    low, high = window
    if low <= high:
        return low <= hour <= high
    return hour >= low or hour <= high


@dataclass(frozen=True)
class _Cluster:
    """Stops grouped as one place."""

    stops: tuple[Stop, ...]

    @property
    def centroid(self) -> GeoPoint:
        return GeoPoint(
            sum(stop.centroid.latitude for stop in self.stops) / len(self.stops),
            sum(stop.centroid.longitude for stop in self.stops) / len(self.stops),
        )

    @property
    def visit_days(self) -> set[date]:
        """Distinct days. Two stops in one day is one visit."""
        return {stop.time_range.start.date() for stop in self.stops}

    def days_within(self, window: tuple[int, int]) -> int:
        return len(
            {
                stop.time_range.start.date()
                for stop in self.stops
                if _within(stop.time_range.start.hour, window)
                or _within(stop.time_range.end.hour, window)
            }
        )

    def weekday_days(self) -> int:
        return len(
            {
                stop.time_range.start.date()
                for stop in self.stops
                if stop.time_range.start.weekday() not in WEEKEND
            }
        )

    def photograph_count(self) -> int:
        return sum(stop.photograph_count for stop in self.stops)

    def period(self) -> TimeRange:
        return TimeRange(
            min(stop.time_range.start for stop in self.stops),
            max(stop.time_range.end for stop in self.stops),
        )


def _group(stops: Sequence[Stop], radius: Distance) -> list[_Cluster]:
    """Grow clusters around a seed until nothing further is close enough."""
    remaining = list(stops)
    clusters: list[list[Stop]] = []

    while remaining:
        group = [remaining.pop(0)]
        growing = True
        while growing:
            growing = False
            centre = GeoPoint(
                sum(stop.centroid.latitude for stop in group) / len(group),
                sum(stop.centroid.longitude for stop in group) / len(group),
            )
            for candidate in list(remaining):
                if centre.distance_to(candidate.centroid) <= radius:
                    group.append(candidate)
                    remaining.remove(candidate)
                    growing = True
        clusters.append(group)

    return [_Cluster(tuple(group)) for group in clusters]


def _area(cluster: _Cluster, settings: AnchorSettings) -> GeoArea:
    centre = cluster.centroid
    spread = max((centre.distance_to(stop.centroid).meters for stop in cluster.stops), default=0.0)
    return GeoArea(centre, Distance(max(spread, settings.cluster_radius.meters)))


def estimate_anchors(
    stops: Sequence[Stop], settings: AnchorSettings | None = None
) -> tuple[Anchor, ...]:
    """Report the places visited on enough separate days, most visited first."""
    rules = settings if settings is not None else AnchorSettings()
    if not stops:
        return ()

    anchors = []
    for cluster in _group(stops, rules.cluster_radius):
        visits = len(cluster.visit_days)
        if visits < rules.min_visits:
            continue
        saturation = rules.min_visits * CONFIDENCE_SATURATES_AT
        anchors.append(
            Anchor(
                area=_area(cluster, rules),
                period=cluster.period(),
                visit_days=visits,
                night_days=cluster.days_within(rules.night_hours),
                weekday_days=cluster.weekday_days(),
                daytime_days=cluster.days_within(rules.working_hours),
                photograph_count=cluster.photograph_count(),
                confidence=Confidence(min(1.0, visits / saturation), visits),
            )
        )

    return tuple(sorted(anchors, key=lambda anchor: anchor.visit_days, reverse=True))
