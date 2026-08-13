"""Shared fixtures for the repository contract suites."""

from datetime import datetime, timedelta, timezone

from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 5, 3, hour, minute, tzinfo=JST)


def photo_id(index: int) -> PhotoId:
    return PhotoId(f"sha256:{index:064x}")


def observation(index: int, hour: int, located: bool = True) -> PhotoObservation:
    place = GeoPoint(35.0 + index * 0.01, 135.0) if located else None
    return PhotoObservation(photo_id(index), at(hour), place)


def stop(
    name: str,
    start: int,
    end: int,
    latitude: float,
    longitude: float,
    photographs: int = 5,
) -> Stop:
    return Stop(
        tuple(PhotoId(f"{name}_{index}") for index in range(photographs)),
        TimeRange(at(start), at(end)),
        GeoPoint(latitude, longitude),
    )


def outing(*stops: Stop) -> Outing:
    return Outing.of(list(stops))


def anchor(visits: int = 52, nights: int = 3) -> Anchor:
    return Anchor(
        area=GeoArea(GeoPoint(34.7810, 135.4700), Distance(500)),
        period=TimeRange(
            datetime(2025, 1, 1, tzinfo=JST), datetime(2026, 8, 1, tzinfo=JST)
        ),
        visit_days=visits,
        night_days=nights,
        weekday_days=visits,
        daytime_days=visits - 5,
        photograph_count=visits * 6,
        confidence=Confidence(1.0, visits),
    )
