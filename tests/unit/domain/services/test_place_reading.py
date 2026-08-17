"""What the owner's own journeys say about each place."""

from datetime import UTC, datetime, timedelta

from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.services.place_reading import derive_place_profiles
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange

BASE = datetime(2026, 6, 1, 12, tzinfo=UTC)
KYOTO = GeoPoint(35.0116, 135.7681)
OSAKA = GeoPoint(34.6937, 135.5023)

_counter = 0


def _stop(point: GeoPoint, days: int) -> Stop:
    global _counter
    _counter += 1
    at = BASE + timedelta(days=days)
    return Stop(
        photo_ids=(PhotoId(f"sha256:{_counter:04d}"),),
        time_range=TimeRange(at, at + timedelta(hours=1)),
        centroid=point,
    )


def _outings(*stops: Stop) -> tuple[Outing, ...]:
    return tuple(Outing.of([stop]) for stop in stops)


def test_nearby_stops_are_one_place():
    nearby = GeoPoint(KYOTO.latitude + 0.0005, KYOTO.longitude)
    places = derive_place_profiles(_outings(_stop(KYOTO, 0), _stop(nearby, 10)))
    assert len(places) == 1
    assert places[0].visits == 2


def test_far_stops_are_two_places():
    places = derive_place_profiles(_outings(_stop(KYOTO, 0), _stop(OSAKA, 1)))
    assert len(places) == 2


def test_the_revisit_gap_is_the_median():
    places = derive_place_profiles(_outings(_stop(KYOTO, 0), _stop(KYOTO, 10), _stop(KYOTO, 30)))
    assert places[0].visits == 3
    assert places[0].median_gap_days == 15


def test_one_visit_has_no_gap():
    places = derive_place_profiles(_outings(_stop(KYOTO, 0)))
    assert places[0].median_gap_days is None
    assert places[0].first_seen == places[0].last_seen


def test_the_most_visited_come_first():
    places = derive_place_profiles(_outings(_stop(OSAKA, 0), _stop(KYOTO, 1), _stop(KYOTO, 2)))
    assert [place.visits for place in places] == [2, 1]
