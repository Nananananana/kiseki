"""Specification for how a person's time away tends to be shaped.

Packed or unhurried, near or far, brief or lingering. These are habits, and they
are what a preference profile is eventually written from.
"""

from datetime import datetime, timedelta, timezone

import pytest
from kiseki.domain.analytics.analytics import summarise_habits
from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))
NEARBY = (34.7800, 135.4650)


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, day, hour, minute, tzinfo=JST)


def stop(
    name: str,
    start: datetime,
    end: datetime,
    place: tuple[float, float],
    photographs: int = 5,
) -> Stop:
    return Stop(
        tuple(PhotoId(f"{name}_{start:%d%H%M}_{index}") for index in range(photographs)),
        TimeRange(start, end),
        GeoPoint(*place),
    )


class TestEmptyInput:
    def test_refuses_to_summarise_nothing(self) -> None:
        """An empty summary would read as a person with no habits."""
        with pytest.raises(ValueError, match="without outings"):
            summarise_habits([])


class TestShape:
    def test_counts_the_outings(self) -> None:
        outings = [
            Outing.of([stop(f"a{day}", at(day, 9), at(day, 11), NEARBY)]) for day in range(1, 4)
        ]
        assert summarise_habits(outings).outing_count == 3

    def test_measures_how_long_an_outing_lasts(self) -> None:
        outings = [Outing.of([stop("a", at(1, 9), at(1, 11), NEARBY)])]
        assert summarise_habits(outings).duration_hours.mean == 2.0

    def test_measures_how_many_stops_are_packed_into_one(self) -> None:
        packed = Outing.of(
            [
                stop("a", at(1, 9), at(1, 10), NEARBY),
                stop("b", at(1, 11), at(1, 12), (NEARBY[0] + 0.01, NEARBY[1])),
                stop("c", at(1, 13), at(1, 14), (NEARBY[0] + 0.02, NEARBY[1])),
            ]
        )
        unhurried = Outing.of([stop("d", at(2, 9), at(2, 17), NEARBY)])
        habits = summarise_habits([packed, unhurried])
        assert habits.stops_per_outing.maximum == 3
        assert habits.stops_per_outing.minimum == 1

    def test_measures_how_long_each_stay_lasts(self) -> None:
        outings = [
            Outing.of(
                [
                    stop("brief", at(1, 9), at(1, 9, 30), NEARBY),
                    stop("long", at(1, 11), at(1, 14), (NEARBY[0] + 0.01, NEARBY[1])),
                ]
            )
        ]
        stays = summarise_habits(outings).stay_minutes
        assert stays.count == 2
        assert stays.minimum == 30
        assert stays.maximum == 180

    def test_a_single_stop_outing_travelled_nothing(self) -> None:
        outings = [Outing.of([stop("a", at(1, 9), at(1, 11), NEARBY)])]
        assert summarise_habits(outings).travel_km.maximum == 0.0

    def test_measures_how_far_an_outing_reaches(self) -> None:
        near = Outing.of(
            [
                stop("a", at(1, 9), at(1, 10), NEARBY),
                stop("b", at(1, 11), at(1, 12), (NEARBY[0] + 0.01, NEARBY[1])),
            ]
        )
        far = Outing.of(
            [
                stop("c", at(2, 9), at(2, 10), NEARBY),
                stop("d", at(2, 14), at(2, 15), (NEARBY[0] + 1.0, NEARBY[1])),
            ]
        )
        travel = summarise_habits([near, far]).travel_km
        assert travel.maximum > 100
        assert travel.minimum < 2

    def test_measures_how_much_someone_photographs(self) -> None:
        outings = [
            Outing.of([stop("few", at(1, 9), at(1, 10), NEARBY, photographs=5)]),
            Outing.of([stop("many", at(2, 9), at(2, 10), NEARBY, photographs=40)]),
        ]
        photographs = summarise_habits(outings).photographs_per_outing
        assert photographs.minimum == 5
        assert photographs.maximum == 40
