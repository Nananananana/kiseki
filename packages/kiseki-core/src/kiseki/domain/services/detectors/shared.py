"""What every stop detector needs, and nothing about how one works."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.settings import StopSettings
from kiseki.domain.shared.time_range import TimeRange


@dataclass(frozen=True)
class StopExtraction:
    """Every photograph appears in exactly one of these three."""

    stops: tuple[Stop, ...]
    in_transit: tuple[PhotoId, ...]
    unlocated: tuple[PhotoId, ...]


@dataclass(frozen=True)
class Located:
    """A photograph known to have coordinates, so the type system stops asking."""

    photo_id: PhotoId
    captured_at: datetime
    location: GeoPoint


def centroid(group: Sequence[Located]) -> GeoPoint:
    return GeoPoint(
        sum(item.location.latitude for item in group) / len(group),
        sum(item.location.longitude for item in group) / len(group),
    )


def located_and_unlocated(
    observations: Sequence[PhotoObservation],
) -> tuple[list[Located], tuple[PhotoId, ...]]:
    """Split the input, and put the located ones in time order.

    Every detector starts here, including the ones that do not care
    about order. Ordering by time **and then by identifier** is what
    makes two runs over one library produce the same stops: two
    photographs sharing a timestamp are common in a merged library,
    and without the tie-break their order would come from whatever the
    database returned.
    """
    unlocated = tuple(item.photo_id for item in observations if item.location is None)
    located = sorted(
        (
            Located(item.photo_id, item.captured_at, item.location)
            for item in observations
            if item.location is not None
        ),
        key=lambda item: (item.captured_at, item.photo_id.value),
    )
    return located, unlocated


def is_a_stay(group: Sequence[Located], span: TimeRange, settings: StopSettings) -> bool:
    """The rule that turns a group into a stop, shared by every detector.

    Deliberately shared. The detectors disagree about *what belongs
    together*, which is the interesting part; they must not also
    disagree about what counts as a stay, or two answers could not be
    compared at all.
    """
    return span.duration >= settings.min_duration or len(group) >= settings.min_photographs


def assemble(
    groups: Sequence[Sequence[Located]], settings: StopSettings
) -> tuple[tuple[Stop, ...], tuple[PhotoId, ...]]:
    """Turn groups into stops, setting aside the ones that are not stays."""
    stops: list[Stop] = []
    in_transit: list[PhotoId] = []
    for group in groups:
        ordered = sorted(group, key=lambda item: item.captured_at)
        span = TimeRange(ordered[0].captured_at, ordered[-1].captured_at)
        if is_a_stay(ordered, span, settings):
            stops.append(Stop(tuple(item.photo_id for item in ordered), span, centroid(ordered)))
        else:
            in_transit.extend(item.photo_id for item in ordered)
    stops.sort(key=lambda stop: stop.time_range.start)
    return tuple(stops), tuple(in_transit)
