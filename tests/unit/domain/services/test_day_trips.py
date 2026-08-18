"""How far the owner already goes, and what sits inside that."""

from datetime import UTC, datetime, timedelta

from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.services.day_trips import (
    QUIET_DAYS,
    REACH_SHARE,
    derive_day_trips,
    derive_reach,
)
from kiseki.domain.services.place_reading import PlaceProfile
from kiseki.domain.services.suggesting import SuggestionKind
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange

TODAY = datetime(2026, 8, 1, 12, tzinfo=UTC)
CENTRE = GeoPoint(34.7810, 135.4690)

_counter = 0


def _stop(point: GeoPoint) -> Stop:
    global _counter
    _counter += 1
    return Stop(
        photo_ids=(PhotoId(f"sha256:{_counter:04d}"),),
        time_range=TimeRange(TODAY, TODAY + timedelta(hours=1)),
        centroid=point,
    )


def _outing(km: float) -> Outing:
    """An outing that moves km away from the centre and no further."""
    degrees = km / 111.0
    return Outing.of([_stop(CENTRE), _stop(GeoPoint(CENTRE.latitude + degrees, CENTRE.longitude))])


def _place(km: float, visits: int, days_ago: int) -> PlaceProfile:
    degrees = km / 111.0
    last = TODAY - timedelta(days=days_ago)
    return PlaceProfile(
        centroid=GeoPoint(CENTRE.latitude + degrees, CENTRE.longitude),
        visits=visits,
        first_seen=last - timedelta(days=30),
        last_seen=last,
        median_gap_days=None,
    )


def _home(visits: int = 40) -> PlaceProfile:
    return PlaceProfile(
        centroid=CENTRE,
        visits=visits,
        first_seen=TODAY - timedelta(days=400),
        last_seen=TODAY,
        median_gap_days=4,
    )


def test_no_outings_means_no_reach() -> None:
    assert derive_reach(()) is None


def test_the_reach_is_the_owner_s_own_distances() -> None:
    reach = derive_reach([_outing(km) for km in (5, 10, 15, 20, 50)])
    assert reach is not None
    assert reach.outings == 5
    assert round(reach.typical_km) == 15
    assert round(reach.usual_km) == 20
    assert reach.share == REACH_SHARE


def test_a_quiet_place_within_reach_is_a_day_trip() -> None:
    reach = derive_reach([_outing(km) for km in (10, 20, 30)])
    assert reach is not None
    trips = derive_day_trips((_home(), _place(15, 1, 300)), reach, TODAY)
    assert len(trips) == 1
    assert trips[0].kind is SuggestionKind.DAY_TRIP
    assert trips[0].distance_km is not None
    assert round(trips[0].distance_km) == 15
    assert trips[0].days_since == 300


def test_somewhere_too_far_is_not_offered() -> None:
    reach = derive_reach([_outing(km) for km in (5, 10, 12)])
    assert reach is not None
    assert derive_day_trips((_home(), _place(400, 1, 300)), reach, TODAY) == ()


def test_somewhere_visited_lately_is_not_offered() -> None:
    reach = derive_reach([_outing(km) for km in (10, 20, 30)])
    assert reach is not None
    assert derive_day_trips((_home(), _place(15, 1, QUIET_DAYS - 1)), reach, TODAY) == ()


def test_a_habit_is_left_to_go_back() -> None:
    """A place with a rhythm belongs to `go back`, not to a day trip."""
    reach = derive_reach([_outing(km) for km in (10, 20, 30)])
    assert reach is not None
    assert derive_day_trips((_home(), _place(15, 9, 300)), reach, TODAY) == ()


def test_the_nearest_come_first() -> None:
    reach = derive_reach([_outing(km) for km in (10, 20, 40)])
    assert reach is not None
    trips = derive_day_trips((_home(), _place(25, 1, 300), _place(8, 2, 400)), reach, TODAY)
    assert [round(trip.distance_km or 0) for trip in trips] == [8, 25]


def test_without_a_centre_nothing_is_offered() -> None:
    reach = derive_reach([_outing(10)])
    assert reach is not None
    assert derive_day_trips((), reach, TODAY) == ()


def test_the_nearest_regular_place_measures() -> None:
    """A life has more than one place it comes from."""
    reach = derive_reach([_outing(km) for km in (5, 8, 9)])
    assert reach is not None
    second_home = PlaceProfile(
        centroid=GeoPoint(CENTRE.latitude + 30 / 111.0, CENTRE.longitude),
        visits=12,
        first_seen=TODAY - timedelta(days=400),
        last_seen=TODAY,
        median_gap_days=7,
    )
    nearby = _place(34, 1, 300)
    trips = derive_day_trips((_home(12), second_home, nearby), reach, TODAY)
    assert len(trips) == 1
    assert trips[0].distance_km is not None
    assert round(trips[0].distance_km) == 4


def _stay(km: float, visits: int, span_days: int, days_ago: int) -> PlaceProfile:
    """A place visited several times, over a span of the caller's choosing."""
    degrees = km / 111.0
    last = TODAY - timedelta(days=days_ago)
    return PlaceProfile(
        centroid=GeoPoint(CENTRE.latitude + degrees, CENTRE.longitude),
        visits=visits,
        first_seen=last - timedelta(days=span_days),
        last_seen=last,
        median_gap_days=span_days // max(1, visits - 1),
    )


def test_a_holiday_is_not_a_base() -> None:
    """Three nights in one town is three visits, not somewhere to set out from."""
    reach = derive_reach([_outing(km) for km in (5, 8, 9)])
    assert reach is not None
    holiday = _stay(500, 3, 3, 400)
    near_the_holiday = PlaceProfile(
        centroid=GeoPoint(CENTRE.latitude + 500 / 111.0 + 0.02, CENTRE.longitude),
        visits=1,
        first_seen=TODAY - timedelta(days=401),
        last_seen=TODAY - timedelta(days=400),
        median_gap_days=None,
    )
    trips = derive_day_trips((_home(), holiday, near_the_holiday), reach, TODAY)
    assert trips == ()


def test_a_day_spent_in_one_place_says_nothing_about_reach() -> None:
    standing_still = Outing.of([_stop(CENTRE)])
    assert derive_reach([standing_still]) is None
    mixed = derive_reach([standing_still, _outing(12)])
    assert mixed is not None
    assert mixed.outings == 1
    assert round(mixed.usual_km) == 12


def test_the_next_street_is_not_a_day_trip() -> None:
    reach = derive_reach([_outing(km) for km in (5, 8, 9)])
    assert reach is not None
    assert derive_day_trips((_home(), _place(0.3, 1, 300)), reach, TODAY) == ()


def test_a_place_a_few_kilometres_out_still_counts() -> None:
    reach = derive_reach([_outing(km) for km in (5, 8, 9)])
    assert reach is not None
    trips = derive_day_trips((_home(), _place(4, 1, 300)), reach, TODAY)
    assert len(trips) == 1


def test_the_longest_gone_comes_first() -> None:
    """Distance decided what is possible; time decides what is worth reading."""
    reach = derive_reach([_outing(km) for km in (10, 30, 40)])
    assert reach is not None
    trips = derive_day_trips((_home(), _place(3, 1, 200), _place(25, 1, 700)), reach, TODAY)
    assert [trip.days_since for trip in trips] == [700, 200]


def test_one_suggestion_per_part_of_town() -> None:
    """Three clusters in one neighbourhood are one place to a reader."""
    reach = derive_reach([_outing(km) for km in (10, 30, 40)])
    assert reach is not None
    trips = derive_day_trips(
        (_home(), _place(5.0, 1, 300), _place(5.5, 1, 400), _place(20, 1, 250)),
        reach,
        TODAY,
    )
    assert len(trips) == 2
    assert [trip.days_since for trip in trips] == [400, 250]


def test_a_single_candidate_still_survives_the_spread() -> None:
    reach = derive_reach([_outing(km) for km in (10, 30, 40)])
    assert reach is not None
    trips = derive_day_trips((_home(), _place(12, 2, 400)), reach, TODAY)
    assert len(trips) == 1
