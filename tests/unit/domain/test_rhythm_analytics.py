"""Specification for when a person tends to go out."""

from datetime import datetime, timedelta, timezone

from kiseki.domain.analytics.analytics import summarise_rhythm
from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))
NEARBY = GeoPoint(34.7800, 135.4650)

SATURDAY = 4
MONDAY = 6


def departing(month: int, day: int, hour: int) -> Outing:
    start = datetime(2026, month, day, hour, tzinfo=JST)
    return Outing.of(
        [
            Stop(
                tuple(PhotoId(f"p_{month}{day}{hour}_{index}") for index in range(5)),
                TimeRange(start, start + timedelta(hours=2)),
                NEARBY,
            )
        ]
    )


class TestEmptyInput:
    def test_reports_zero_rather_than_failing(self) -> None:
        rhythm = summarise_rhythm([])
        assert rhythm.weekend_share == 0.0
        assert rhythm.early_start_share == 0.0
        assert rhythm.by_month == {}

    def test_every_weekday_and_hour_is_present_even_at_zero(self) -> None:
        """A consumer can render a full week or a full day without filling gaps."""
        rhythm = summarise_rhythm([])
        assert len(rhythm.by_weekday) == 7
        assert len(rhythm.by_departure_hour) == 24


class TestWeekends:
    def test_measures_the_weekend_share(self) -> None:
        rhythm = summarise_rhythm([departing(4, SATURDAY, 10), departing(4, MONDAY, 10)])
        assert rhythm.weekend_share == 0.5

    def test_counts_outings_by_weekday(self) -> None:
        rhythm = summarise_rhythm([departing(4, SATURDAY, 10), departing(4, MONDAY, 10)])
        assert rhythm.by_weekday["Sat"] == 1
        assert rhythm.by_weekday["Mon"] == 1
        assert rhythm.by_weekday["Wed"] == 0


class TestDepartureTime:
    def test_counts_outings_by_departure_hour(self) -> None:
        rhythm = summarise_rhythm([departing(4, 1, 7), departing(4, 2, 14)])
        assert rhythm.by_departure_hour[7] == 1
        assert rhythm.by_departure_hour[14] == 1

    def test_measures_the_share_of_early_starts(self) -> None:
        """Leaving before nine and leaving after lunch are different habits."""
        rhythm = summarise_rhythm([departing(4, 1, 7), departing(4, 2, 14)])
        assert rhythm.early_start_share == 0.5

    def test_what_counts_as_early_is_configurable(self) -> None:
        rhythm = summarise_rhythm([departing(4, 1, 7), departing(4, 2, 14)], early_hour=6)
        assert rhythm.early_start_share == 0.0


class TestSeasons:
    def test_counts_outings_by_month(self) -> None:
        outings = [departing(4, 1, 10), departing(4, 2, 10), departing(8, 1, 10)]
        assert summarise_rhythm(outings).by_month == {"2026-04": 2, "2026-08": 1}

    def test_months_are_in_order(self) -> None:
        outings = [departing(11, 1, 10), departing(2, 1, 10), departing(7, 1, 10)]
        assert list(summarise_rhythm(outings).by_month) == ["2026-02", "2026-07", "2026-11"]
