"""Finding the places a person returns to.

Distance from home cannot be used to identify home, so the signal has to be
frequency and timing instead. A place slept at is residential. A place visited
on weekday afternoons and never slept at is a workplace. Everything else, however
far away, is somewhere the person went rather than somewhere they are based.

This ordering also means the definition works for anyone: it never assumes a
particular city size, a commute length, or that travel means going far.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from kiseki.domain.anchor.anchor import Anchor, AnchorKind
from kiseki.domain.outing.stop import Stop
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.settings import AnchorSettings
from kiseki.domain.shared.time_range import TimeRange

WEEKEND = (5, 6)
CONFIDENCE_SATURATES_AT = 4
"""Visits beyond min_visits times this give no further confidence."""


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
    def visit_days(self) -> set[object]:
        """Distinct days, not stops. Two visits in one day is one visit."""
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

    def stops_within(self, window: tuple[int, int]) -> int:
        return sum(
            1
            for stop in self.stops
            if _within(stop.time_range.start.hour, window)
            or _within(stop.time_range.end.hour, window)
        )

    def weekday_stops(self) -> int:
        return sum(1 for stop in self.stops if stop.time_range.start.weekday() not in WEEKEND)

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


def _classify(
    cluster: _Cluster, nights: int, is_most_slept_at: bool, settings: AnchorSettings
) -> AnchorKind | None:
    """Decide what sort of base this is, or that it is not a base at all.

    Returning None matters as much as the three kinds. A cafe visited every
    weekend is frequent, but it is somewhere the person chose to go, not
    somewhere they operate from. Calling it an anchor would remove it from the
    outings and with it the strongest evidence of what they like.
    """
    if is_most_slept_at and nights > 0:
        return AnchorKind.PRIMARY
    if nights >= settings.secondary_min_nights:
        return AnchorKind.SECONDARY

    total = len(cluster.stops)
    mostly_weekdays = cluster.weekday_stops() > total / 2
    mostly_working_hours = cluster.stops_within(settings.working_hours) > total / 2
    if mostly_weekdays and mostly_working_hours:
        return AnchorKind.WORKPLACE

    return None


def _area(cluster: _Cluster, settings: AnchorSettings) -> GeoArea:
    centre = cluster.centroid
    spread = max((centre.distance_to(stop.centroid).meters for stop in cluster.stops), default=0.0)
    return GeoArea(centre, Distance(max(spread, settings.cluster_radius.meters)))


def estimate_anchors(
    stops: Sequence[Stop], settings: AnchorSettings | None = None
) -> tuple[Anchor, ...]:
    """Identify the places returned to, ordered with the most slept at first."""
    rules = settings if settings is not None else AnchorSettings()
    if not stops:
        return ()

    candidates = [
        cluster
        for cluster in _group(stops, rules.cluster_radius)
        if len(cluster.visit_days) >= rules.min_visits
    ]
    if not candidates:
        return ()

    ranked = sorted(
        ((cluster, cluster.days_within(rules.night_hours)) for cluster in candidates),
        key=lambda pair: (pair[1], len(pair[0].visit_days)),
        reverse=True,
    )

    anchors = []
    for index, (cluster, nights) in enumerate(ranked):
        kind = _classify(cluster, nights, index == 0, rules)
        if kind is None:
            continue

        visits = len(cluster.visit_days)
        saturation = rules.min_visits * CONFIDENCE_SATURATES_AT
        anchors.append(
            Anchor(
                kind=kind,
                area=_area(cluster, rules),
                period=cluster.period(),
                visit_count=visits,
                night_count=nights,
                confidence=Confidence(min(1.0, visits / saturation), visits),
            )
        )
    return tuple(anchors)
