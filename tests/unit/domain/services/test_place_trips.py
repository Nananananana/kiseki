"""A place visited only on holidays is not somewhere to go back to."""

from datetime import UTC, datetime, timedelta

from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.services.place_reading import derive_place_profiles
from kiseki.domain.services.suggesting import derive_suggestions
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange

BASE = datetime(2026, 1, 1, 9, tzinfo=UTC)
AIRPORT = GeoPoint(34.4342, 135.2325)

_counter = 0


def _outing(days: int, where: GeoPoint) -> Outing:
    global _counter
    _counter += 1
    start = BASE + timedelta(days=days)
    return Outing.of(
        [
            Stop(
                photo_ids=(PhotoId(f"sha256:{_counter:04d}"),),
                time_range=TimeRange(start, start + timedelta(hours=2)),
                centroid=where,
            )
        ]
    )


def test_a_place_counts_the_visits_that_were_on_a_trip() -> None:
    outings = [_outing(0, AIRPORT), _outing(90, AIRPORT), _outing(180, AIRPORT)]
    on_trips = {outings[0].id.value, outings[1].id.value}
    places = derive_place_profiles(outings, on_trips)
    assert places[0].visits == 3
    assert places[0].trip_visits == 2
    assert not places[0].only_on_trips


def test_a_place_seen_only_while_away_says_so() -> None:
    outings = [_outing(0, AIRPORT), _outing(120, AIRPORT), _outing(300, AIRPORT)]
    everything = {outing.id.value for outing in outings}
    places = derive_place_profiles(outings, everything)
    assert places[0].only_on_trips


def test_without_trips_nothing_is_marked() -> None:
    outings = [_outing(0, AIRPORT), _outing(90, AIRPORT)]
    assert derive_place_profiles(outings)[0].trip_visits == 0


def test_go_back_is_not_offered_for_somewhere_only_ever_passed_through() -> None:
    """An airport on the way to every holiday has a tidy cadence and no meaning."""
    outings = [_outing(day, AIRPORT) for day in (0, 90, 180, 270)]
    everything = {outing.id.value for outing in outings}
    places = derive_place_profiles(outings, everything)
    today = BASE + timedelta(days=900)
    assert derive_suggestions(places, None, today) == ()


def test_the_same_place_visited_off_trip_is_still_offered() -> None:
    outings = [_outing(day, AIRPORT) for day in (0, 90, 180, 270)]
    places = derive_place_profiles(outings, {outings[0].id.value})
    today = BASE + timedelta(days=900)
    suggestions = derive_suggestions(places, None, today)
    assert len(suggestions) == 1
