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
    return Outing.of(
        [_stop(CENTRE), _stop(GeoPoint(CENTRE.latitude + degrees, CENTRE.longitude))]
    )


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
    assert round(reach.typical_km) == 20
    assert round(reach.usual_km) == 40
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
    trips = derive_day_trips(
        (_home(), _place(25, 1, 300), _place(8, 2, 400)), reach, TODAY
    )
    assert [round(trip.distance_km or 0) for trip in trips] == [8, 25]


def test_without_a_centre_nothing_is_offered() -> None:
    reach = derive_reach([_outing(10)])
    assert reach is not None
    assert derive_day_trips((), reach, TODAY) == ()
