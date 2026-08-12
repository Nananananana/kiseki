"""Specification for anchor estimation.

An anchor is a place returned to repeatedly. Which kind of place it is follows
from when it is visited: sleeping somewhere makes it residential, spending
weekday afternoons there makes it a workplace.
"""

from datetime import datetime, timedelta, timezone

from kiseki.domain.anchor.anchor import AnchorKind
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.services.anchor_estimation import estimate_anchors
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.domain.shared.settings import AnchorSettings
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))
HOME = (34.7810, 135.4700)
WORKPLACE = (34.7020, 135.4960)
FAMILY = (35.0116, 135.7681)
ELSEWHERE = (43.0687, 141.3508)


def stop(
    name: str,
    day: int,
    start_hour: int,
    end_hour: int,
    place: tuple[float, float],
    jitter: float = 0.0,
) -> Stop:
    return Stop(
        tuple(PhotoId(f"{name}_{day}_{index}") for index in range(5)),
        TimeRange(
            datetime(2026, 6, day, start_hour, tzinfo=JST),
            datetime(2026, 6, day, end_hour, tzinfo=JST),
        ),
        GeoPoint(place[0] + jitter, place[1] + jitter),
    )


def nightly(place: tuple[float, float], days: range, name: str = "n") -> list[Stop]:
    return [stop(name, day, 21, 23, place, jitter=0.0002 * (day % 3)) for day in days]


def daily(place: tuple[float, float], days: range, name: str = "d") -> list[Stop]:
    return [stop(name, day, 10, 16, place, jitter=0.0001 * (day % 3)) for day in days]


class TestEmptyAndSparseInput:
    def test_nothing_in_nothing_out(self) -> None:
        assert estimate_anchors([]) == ()

    def test_a_place_visited_a_few_times_is_not_an_anchor(self) -> None:
        """Returning three times is not yet a pattern."""
        assert estimate_anchors(nightly(HOME, range(1, 4))) == ()

    def test_a_single_trip_is_never_an_anchor(self) -> None:
        stops = [*nightly(HOME, range(1, 11)), stop("trip", 15, 12, 18, ELSEWHERE)]
        places = [anchor.area.center for anchor in estimate_anchors(stops)]
        assert all(place.latitude < 40 for place in places)


class TestClassification:
    def test_sleeping_somewhere_makes_it_primary(self) -> None:
        anchors = estimate_anchors(nightly(HOME, range(1, 11)))
        assert len(anchors) == 1
        assert anchors[0].kind == AnchorKind.PRIMARY

    def test_weekday_afternoons_make_it_a_workplace(self) -> None:
        anchors = estimate_anchors(daily(WORKPLACE, range(1, 21)))
        assert anchors[0].kind == AnchorKind.WORKPLACE

    def test_a_second_place_slept_at_is_secondary(self) -> None:
        """A family home stayed at regularly is not where you live."""
        stops = nightly(HOME, range(1, 26), "home") + nightly(FAMILY, range(1, 26, 3), "family")
        anchors = estimate_anchors(stops)
        kinds = {anchor.kind for anchor in anchors}
        assert AnchorKind.PRIMARY in kinds
        assert AnchorKind.SECONDARY in kinds

    def test_the_home_is_the_place_with_the_most_nights(self) -> None:
        stops = nightly(HOME, range(1, 21), "home") + nightly(FAMILY, range(1, 11), "family")
        anchors = estimate_anchors(stops)
        assert anchors[0].kind == AnchorKind.PRIMARY
        assert anchors[0].area.contains(GeoPoint(*HOME))


class TestNightsAcrossMidnight:
    def test_a_late_evening_counts_as_a_night(self) -> None:
        anchors = estimate_anchors(nightly(HOME, range(1, 11)))
        assert anchors[0].night_count == 10

    def test_the_small_hours_count_too(self) -> None:
        """The night window wraps past midnight, as a night does."""
        stops = [stop("late", day, 2, 3, HOME) for day in range(1, 11)]
        assert estimate_anchors(stops)[0].night_count == 10


class TestGrouping:
    def test_distinct_places_stay_distinct(self) -> None:
        stops = nightly(HOME, range(1, 11), "home") + nightly(
            (HOME[0] + 0.02, HOME[1]), range(1, 11), "other"
        )
        assert len(estimate_anchors(stops)) == 2

    def test_a_larger_radius_merges_them(self) -> None:
        stops = nightly(HOME, range(1, 11), "home") + nightly(
            (HOME[0] + 0.02, HOME[1]), range(1, 11), "other"
        )
        settings = AnchorSettings(cluster_radius=Distance(5000))
        assert len(estimate_anchors(stops, settings)) == 1

    def test_gps_wander_does_not_split_a_home(self) -> None:
        assert len(estimate_anchors(nightly(HOME, range(1, 26)))) == 1


class TestReportedValues:
    def test_counts_the_days_visited_not_the_stops(self) -> None:
        """Two stops on one day is one visit."""
        stops = nightly(HOME, range(1, 11), "evening") + [
            stop("morning", day, 6, 7, HOME) for day in range(1, 11)
        ]
        assert estimate_anchors(stops)[0].visit_count == 10

    def test_the_period_spans_the_first_and_last_visit(self) -> None:
        anchor = estimate_anchors(nightly(HOME, range(1, 11)))[0]
        assert anchor.period.start.day == 1
        assert anchor.period.end.day == 10

    def test_confidence_records_how_many_visits_it_rests_on(self) -> None:
        anchor = estimate_anchors(nightly(HOME, range(1, 11)))[0]
        assert anchor.confidence.sample_size == 10

    def test_more_visits_give_more_confidence(self) -> None:
        few = estimate_anchors(nightly(HOME, range(1, 11)))[0]
        many = estimate_anchors(nightly(HOME, range(1, 26)))[0]
        assert many.confidence.value > few.confidence.value


class TestSettings:
    def test_a_higher_visit_threshold_excludes_more(self) -> None:
        stops = nightly(HOME, range(1, 11))
        assert estimate_anchors(stops) != ()
        assert estimate_anchors(stops, AnchorSettings(min_visits=20)) == ()

    def test_defaults_apply_when_none_are_given(self) -> None:
        stops = nightly(HOME, range(1, 11))
        assert estimate_anchors(stops) == estimate_anchors(stops, AnchorSettings())
