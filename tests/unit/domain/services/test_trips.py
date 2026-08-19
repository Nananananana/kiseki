"""A night away is one journey, not three days of them."""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.services.trips import AWAY_KM, Trip, derive_trips
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange

HOME = GeoPoint(34.7810, 135.4690)
SEOUL = GeoPoint(37.5600, 126.9800)
KYOTO = GeoPoint(35.0116, 135.7681)

_counter = 0


def _outing(day: int, hour: int, where: GeoPoint, hours: int = 3) -> Outing:
    global _counter
    _counter += 1
    start = datetime(2026, 3, day, hour, tzinfo=UTC)
    stop = Stop(
        photo_ids=(PhotoId(f"sha256:{_counter:04d}"),),
        time_range=TimeRange(start, start + timedelta(hours=hours)),
        centroid=where,
    )
    return Outing.of([stop])


def test_three_days_in_one_city_are_one_trip() -> None:
    outings = [_outing(19, 12, SEOUL), _outing(20, 10, SEOUL), _outing(21, 9, SEOUL)]
    trips = derive_trips(outings, [HOME])
    assert len(trips) == 1
    assert trips[0].nights == 2
    assert len(trips[0].outings) == 3
    assert trips[0].farthest_km > AWAY_KM


def test_a_day_out_is_not_a_trip() -> None:
    """Kyoto and back is far enough to be a day trip and no night away."""
    assert derive_trips([_outing(5, 9, KYOTO)], [HOME]) == ()


def test_one_distant_day_is_not_a_trip_either() -> None:
    assert derive_trips([_outing(5, 9, SEOUL)], [HOME]) == ()


def test_a_fortnight_between_them_is_two_trips() -> None:
    outings = [
        _outing(1, 9, SEOUL),
        _outing(2, 9, SEOUL),
        _outing(20, 9, SEOUL),
        _outing(21, 9, SEOUL),
    ]
    trips = derive_trips(outings, [HOME])
    assert [trip.start.day for trip in trips] == [1, 20]


def test_staying_near_home_is_never_a_trip() -> None:
    outings = [_outing(1, 9, HOME), _outing(2, 9, HOME)]
    assert derive_trips(outings, [HOME]) == ()


def test_an_outing_that_touches_home_is_not_away() -> None:
    """A run that passes through the everyday is not one going."""
    global _counter
    _counter += 1
    start = datetime(2026, 3, 10, 9, tzinfo=UTC)
    mixed = Outing.of(
        [
            Stop(
                photo_ids=(PhotoId(f"sha256:{_counter:04d}a"),),
                time_range=TimeRange(start, start + timedelta(hours=1)),
                centroid=HOME,
            ),
            Stop(
                photo_ids=(PhotoId(f"sha256:{_counter:04d}b"),),
                time_range=TimeRange(start + timedelta(hours=6), start + timedelta(hours=8)),
                centroid=SEOUL,
            ),
        ]
    )
    assert derive_trips([mixed, _outing(11, 9, SEOUL)], [HOME]) == ()


def test_without_a_place_to_leave_from_nothing_is_a_trip() -> None:
    outings = [_outing(19, 12, SEOUL), _outing(20, 10, SEOUL)]
    assert derive_trips(outings, []) == ()


def test_a_trip_spans_a_night_by_definition() -> None:
    with pytest.raises(ValueError):
        Trip(outings=(_outing(1, 9, SEOUL),), farthest_km=800.0)
