"""Specification for the Outing aggregate."""

from datetime import datetime, timedelta, timezone

import pytest
from kiseki.domain.outing.outing import Outing, OutingId
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2025, 5, 3, hour, minute, tzinfo=JST)


def stop(name: str, start: int, end: int, latitude: float, longitude: float) -> Stop:
    return Stop(
        tuple(PhotoId(f"{name}{index}") for index in range(3)),
        TimeRange(at(start), at(end)),
        GeoPoint(latitude, longitude),
    )


PARK = stop("park", 9, 11, 35.0094, 135.6669)
LUNCH = stop("lunch", 12, 13, 35.0150, 135.6780)
MUSEUM = stop("museum", 14, 16, 35.0250, 135.7600)


class TestConstruction:
    def test_rejects_an_outing_with_no_stops(self) -> None:
        with pytest.raises(ValueError, match="at least one stop"):
            Outing(OutingId("abc"), ())

    def test_orders_its_stops_by_time(self) -> None:
        outing = Outing.of([MUSEUM, PARK, LUNCH])
        assert outing.stops == (PARK, LUNCH, MUSEUM)


class TestDerivedValues:
    def test_spans_from_the_first_arrival_to_the_last_departure(self) -> None:
        outing = Outing.of([PARK, LUNCH, MUSEUM])
        assert outing.time_range.start == at(9)
        assert outing.time_range.end == at(16)

    def test_reports_its_duration(self) -> None:
        assert Outing.of([PARK, MUSEUM]).duration == timedelta(hours=7)

    def test_counts_stops_and_photographs(self) -> None:
        outing = Outing.of([PARK, LUNCH, MUSEUM])
        assert outing.stop_count == 3
        assert outing.photograph_count == 9

    def test_measures_the_distance_travelled_between_stops(self) -> None:
        outing = Outing.of([PARK, LUNCH, MUSEUM])
        direct = PARK.centroid.distance_to(LUNCH.centroid).meters
        onward = LUNCH.centroid.distance_to(MUSEUM.centroid).meters
        assert outing.travelled.meters == pytest.approx(direct + onward)

    def test_a_single_stop_outing_travelled_nothing(self) -> None:
        assert Outing.of([PARK]).travelled.meters == 0


class TestIdentity:
    def test_the_identifier_is_derived_from_the_photographs(self) -> None:
        """Outings are recomputed from scratch, so identity must come from content."""
        assert Outing.of([PARK, LUNCH]).id == Outing.of([PARK, LUNCH]).id

    def test_the_order_of_the_input_does_not_change_it(self) -> None:
        assert Outing.of([LUNCH, PARK]).id == Outing.of([PARK, LUNCH]).id

    def test_a_different_set_of_stops_gives_a_different_identifier(self) -> None:
        assert Outing.of([PARK, LUNCH]).id != Outing.of([PARK, LUNCH, MUSEUM]).id
