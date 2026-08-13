"""Specification for anchor estimation.

An anchor is a place photographed on enough separate days to be part of someone's
life. The service says what was observed there and nothing more: naming a place
a home or a workplace depends on how a person lives, and gets it wrong as often
as right. See ADR-0012.
"""

from datetime import datetime, timedelta, timezone

from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.services.anchor_estimation import estimate_anchors
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.domain.shared.settings import AnchorSettings
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))
HOME = (34.7810, 135.4700)
OTHER = (35.0116, 135.7681)
ELSEWHERE = (43.0687, 141.3508)

WEEKEND_DAYS = (6, 7, 13, 14, 20, 21, 27, 28)
WEEKDAY_DAYS = (1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 15, 16, 17, 18, 19, 22, 23, 24, 25)


def stop(
    name: str,
    day: int,
    start_hour: int,
    end_hour: int,
    place: tuple[float, float],
    photographs: int = 5,
    jitter: float = 0.0,
) -> Stop:
    return Stop(
        tuple(PhotoId(f"{name}_{day}_{index}") for index in range(photographs)),
        TimeRange(
            datetime(2026, 6, day, start_hour, tzinfo=JST),
            datetime(2026, 6, day, end_hour, tzinfo=JST),
        ),
        GeoPoint(place[0] + jitter, place[1] + jitter),
    )


def nightly(place: tuple[float, float], days: range, name: str = "n") -> list[Stop]:
    return [stop(name, day, 21, 23, place, jitter=0.0002 * (day % 3)) for day in days]


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


class TestWhatIsObserved:
    def test_a_place_slept_at_has_a_high_night_share(self) -> None:
        anchors = estimate_anchors(nightly(HOME, range(1, 11)))
        assert len(anchors) == 1
        assert anchors[0].night_share == 1.0

    def test_a_place_used_on_weekday_afternoons_shows_that_instead(self) -> None:
        stops = [stop("office", day, 13, 15, HOME) for day in WEEKDAY_DAYS]
        anchor = estimate_anchors(stops)[0]
        assert anchor.night_share == 0.0
        assert anchor.weekday_share == 1.0
        assert anchor.daytime_share == 1.0

    def test_a_weekend_haunt_shows_that_instead_again(self) -> None:
        """No category is assigned. The numbers say what kind of place it is."""
        stops = [stop("cafe", day, 13, 15, HOME) for day in WEEKEND_DAYS]
        anchor = estimate_anchors(stops)[0]
        assert anchor.night_share == 0.0
        assert anchor.weekday_share == 0.0
        assert anchor.daytime_share == 1.0

    def test_counts_photographs_as_well_as_visits(self) -> None:
        stops = [stop("p", day, 13, 15, HOME, photographs=10) for day in WEEKEND_DAYS]
        anchor = estimate_anchors(stops)[0]
        assert anchor.photograph_count == 80
        assert anchor.photographs_per_visit == 10


class TestNightsAcrossMidnight:
    def test_a_late_evening_counts_as_a_night(self) -> None:
        assert estimate_anchors(nightly(HOME, range(1, 11)))[0].night_days == 10

    def test_the_small_hours_count_too(self) -> None:
        """The night window wraps past midnight, as a night does."""
        stops = [stop("late", day, 2, 3, HOME) for day in range(1, 11)]
        assert estimate_anchors(stops)[0].night_days == 10


class TestGrouping:
    def test_distinct_places_stay_distinct(self) -> None:
        stops = [
            *nightly(HOME, range(1, 11), "home"),
            *nightly((HOME[0] + 0.02, HOME[1]), range(1, 11), "other"),
        ]
        assert len(estimate_anchors(stops)) == 2

    def test_a_larger_radius_merges_them(self) -> None:
        stops = [
            *nightly(HOME, range(1, 11), "home"),
            *nightly((HOME[0] + 0.02, HOME[1]), range(1, 11), "other"),
        ]
        assert len(estimate_anchors(stops, AnchorSettings(cluster_radius=Distance(5000)))) == 1

    def test_gps_wander_does_not_split_a_place(self) -> None:
        assert len(estimate_anchors(nightly(HOME, range(1, 26)))) == 1


class TestReportedValues:
    def test_counts_the_days_visited_not_the_stops(self) -> None:
        """Two stops on one day is one visit."""
        stops = [
            *nightly(HOME, range(1, 11), "evening"),
            *[stop("morning", day, 6, 7, HOME) for day in range(1, 11)],
        ]
        assert estimate_anchors(stops)[0].visit_days == 10

    def test_the_period_spans_the_first_and_last_visit(self) -> None:
        anchor = estimate_anchors(nightly(HOME, range(1, 11)))[0]
        assert anchor.period.start.day == 1
        assert anchor.period.end.day == 10

    def test_confidence_records_how_many_visits_it_rests_on(self) -> None:
        assert estimate_anchors(nightly(HOME, range(1, 11)))[0].confidence.sample_size == 10

    def test_more_visits_give_more_confidence(self) -> None:
        few = estimate_anchors(nightly(HOME, range(1, 11)))[0]
        many = estimate_anchors(nightly(HOME, range(1, 26)))[0]
        assert many.confidence.value > few.confidence.value


class TestOrdering:
    def test_the_most_visited_place_comes_first(self) -> None:
        stops = [
            *nightly(HOME, range(1, 21), "home"),
            *nightly(OTHER, range(1, 11), "other"),
        ]
        assert estimate_anchors(stops)[0].visit_days == 20


class TestSettings:
    def test_a_higher_visit_threshold_excludes_more(self) -> None:
        stops = nightly(HOME, range(1, 11))
        assert estimate_anchors(stops) != ()
        assert estimate_anchors(stops, AnchorSettings(min_visits=20)) == ()

    def test_defaults_apply_when_none_are_given(self) -> None:
        stops = nightly(HOME, range(1, 11))
        assert estimate_anchors(stops) == estimate_anchors(stops, AnchorSettings())
