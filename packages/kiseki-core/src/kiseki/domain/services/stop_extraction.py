"""Separating stays from journeys.

The only evidence available is when and where photographs were taken. A stay
shows up as a cluster in space that persists in time; a journey shows up as
photographs strung out along a line, taken faster than anyone walks.

Two signals decide whether the next photograph continues the current stay.
Proximity to the centre of the stay handles GPS wander and moving around a
site. Speed since the previous photograph handles the case where someone drifts
gradually across a large area, which proximity alone would split.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.settings import StopSettings
from kiseki.domain.shared.speed import Speed
from kiseki.domain.shared.time_range import TimeRange


@dataclass(frozen=True)
class StopExtraction:
    """Every photograph appears in exactly one of these three."""

    stops: tuple[Stop, ...]
    in_transit: tuple[PhotoId, ...]
    unlocated: tuple[PhotoId, ...]


@dataclass(frozen=True)
class _Located:
    """A photograph known to have coordinates, so the type system stops asking."""

    photo_id: PhotoId
    captured_at: datetime
    location: GeoPoint


def _centroid(group: Sequence[_Located]) -> GeoPoint:
    return GeoPoint(
        sum(item.location.latitude for item in group) / len(group),
        sum(item.location.longitude for item in group) / len(group),
    )


def _continues(group: Sequence[_Located], candidate: _Located, settings: StopSettings) -> bool:
    previous = group[-1]
    gap = candidate.captured_at - previous.captured_at

    if gap > settings.max_gap:
        return False
    if _centroid(group).distance_to(candidate.location) <= settings.stay_radius:
        return True
    if gap.total_seconds() <= 0:
        return False

    travelled = previous.location.distance_to(candidate.location)
    return Speed.between(travelled, gap) <= settings.drift_speed


def _is_a_stay(group: Sequence[_Located], span: TimeRange, settings: StopSettings) -> bool:
    return span.duration >= settings.min_duration or len(group) >= settings.min_photographs


def extract_stops(
    observations: Sequence[PhotoObservation], settings: StopSettings | None = None
) -> StopExtraction:
    """Group photographs into stays.

    Photographs without coordinates are set aside rather than discarded; they
    can still be placed by time once outings are assembled.
    """
    rules = settings if settings is not None else StopSettings()

    unlocated = tuple(item.photo_id for item in observations if item.location is None)
    located = sorted(
        (
            _Located(item.photo_id, item.captured_at, item.location)
            for item in observations
            if item.location is not None
        ),
        key=lambda item: item.captured_at,
    )

    groups: list[list[_Located]] = []
    for item in located:
        if groups and _continues(groups[-1], item, rules):
            groups[-1].append(item)
        else:
            groups.append([item])

    stops: list[Stop] = []
    in_transit: list[PhotoId] = []
    for group in groups:
        span = TimeRange(group[0].captured_at, group[-1].captured_at)
        if _is_a_stay(group, span, rules):
            stops.append(Stop(tuple(item.photo_id for item in group), span, _centroid(group)))
        else:
            in_transit.extend(item.photo_id for item in group)

    return StopExtraction(tuple(stops), tuple(in_transit), unlocated)
