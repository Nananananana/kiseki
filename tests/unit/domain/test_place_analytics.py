"""Specification for what a pattern of visits says about a person.

These measures are about preference, not geography. Whether someone returns to
places they liked, and what share of places they never see again, says more
about them than where those places happen to be.
"""

from datetime import datetime, timedelta, timezone

from kiseki.domain.analytics.analytics import summarise_places
from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))
NEARBY = (34.7800, 135.4650)
RADIUS = Distance(500)


def at(month: int, day: int, hour: int) -> datetime:
    return datetime(2026, month, day, hour, tzinfo=JST)


def stop(
    name: str,
    start: datetime,
    end: datetime,
    place: tuple[float, float],
    photographs: int = 5,
    jitter: float = 0.0,
) -> Stop:
    return Stop(
        tuple(PhotoId(f"{name}_{start:%m%d%H}_{index}") for index in range(photographs)),
        TimeRange(start, end),
        GeoPoint(place[0] + jitter, place[1] + jitter),
    )


def visit(
    name: str,
    month: int,
    day: int,
    place: tuple[float, float],
    photographs: int = 5,
    jitter: float = 0.0,
) -> Outing:
    return Outing.of(
        [
            stop(
                name,
                at(month, day, 10),
                at(month, day, 11),
                place,
                photographs=photographs,
                jitter=jitter,
            )
        ]
    )


class TestEmptyInput:
    def test_no_outings_yields_no_places(self) -> None:
        result = summarise_places([], RADIUS)
        assert result.places == ()
        assert result.return_rate == 0.0
        assert result.most_returned_to == ()


class TestReturnRate:
    def test_places_never_seen_again_give_a_zero_return_rate(self) -> None:
        outings = [visit(f"x{index}", 4, index + 1, (34.0 + index, 135.0)) for index in range(3)]
        result = summarise_places(outings, RADIUS)
        assert result.return_rate == 0.0
        assert result.one_time_rate == 1.0

    def test_going_back_raises_it(self) -> None:
        outings = [visit(f"s{index}", 4, index + 1, NEARBY) for index in range(4)]
        result = summarise_places(outings, RADIUS)
        assert result.return_rate == 1.0
        assert result.places[0].visit_days == 4

    def test_the_two_rates_are_complements(self) -> None:
        outings = [
            *[visit(f"a{index}", 4, index + 1, NEARBY) for index in range(3)],
            visit("b", 5, 1, (35.5, 136.0)),
        ]
        result = summarise_places(outings, RADIUS)
        assert result.return_rate + result.one_time_rate == 1.0


class TestCountingVisits:
    def test_two_stops_on_one_day_are_one_visit(self) -> None:
        """Photographing somewhere morning and evening is one day of evidence."""
        outings = [
            Outing.of([stop("morning", at(4, 1, 9), at(4, 1, 10), NEARBY)]),
            Outing.of([stop("evening", at(4, 1, 19), at(4, 1, 20), NEARBY)]),
        ]
        assert summarise_places(outings, RADIUS).places[0].visit_days == 1

    def test_records_the_first_and_last_visit(self) -> None:
        outings = [visit("a", 4, 1, NEARBY), visit("b", 6, 15, NEARBY)]
        place = summarise_places(outings, RADIUS).places[0]
        assert place.first_visit == at(4, 1, 10).date()
        assert place.last_visit == at(6, 15, 10).date()

    def test_reports_photographs_per_visit(self) -> None:
        """How much someone photographs a place is a measure of interest in it."""
        outings = [
            visit("a", 4, 1, NEARBY, photographs=10),
            visit("b", 4, 2, NEARBY, photographs=20),
        ]
        assert summarise_places(outings, RADIUS).places[0].photographs_per_visit == 15


class TestGrouping:
    def test_nearby_stops_are_the_same_place(self) -> None:
        outings = [
            visit(f"n{index}", 4, index + 1, NEARBY, jitter=0.001) for index in range(3)
        ]
        assert len(summarise_places(outings, RADIUS).places) == 1

    def test_distant_stops_are_different_places(self) -> None:
        outings = [
            *[visit(f"n{index}", 4, index + 1, NEARBY) for index in range(3)],
            *[
                visit(f"f{index}", 5, index + 1, (NEARBY[0] + 0.02, NEARBY[1]))
                for index in range(3)
            ],
        ]
        assert len(summarise_places(outings, RADIUS).places) == 2

    def test_a_wider_radius_merges_them(self) -> None:
        outings = [
            *[visit(f"n{index}", 4, index + 1, NEARBY) for index in range(3)],
            *[
                visit(f"f{index}", 5, index + 1, (NEARBY[0] + 0.02, NEARBY[1]))
                for index in range(3)
            ],
        ]
        assert len(summarise_places(outings, Distance(5000)).places) == 1


class TestRanking:
    def test_the_most_visited_place_comes_first(self) -> None:
        outings = [
            *[visit(f"often{index}", 4, index + 1, NEARBY) for index in range(5)],
            *[
                visit(f"rarely{index}", 5, index + 1, (NEARBY[0] + 0.05, NEARBY[1]))
                for index in range(2)
            ],
        ]
        assert summarise_places(outings, RADIUS).places[0].visit_days == 5

    def test_only_returned_to_places_appear_in_the_highlights(self) -> None:
        outings = [
            *[visit(f"often{index}", 4, index + 1, NEARBY) for index in range(3)],
            visit("once", 5, 1, (35.5, 136.0)),
        ]
        result = summarise_places(outings, RADIUS)
        assert len(result.most_returned_to) == 1

    def test_the_highlights_are_limited(self) -> None:
        outings = [
            visit(f"p{group}_{index}", 4, index + 1, (34.0 + group, 135.0))
            for group in range(6)
            for index in range(2)
        ]
        assert len(summarise_places(outings, RADIUS, top=3).most_returned_to) == 3
