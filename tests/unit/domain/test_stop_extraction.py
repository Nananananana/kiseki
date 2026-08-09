"""Specification for stop extraction.

A stop is a stay at one place. The problem is separating a stay from a journey
using nothing but the times and places of photographs.
"""

from datetime import datetime, timedelta, timezone

from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.services.stop_extraction import extract_stops
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.domain.shared.settings import StopSettings
from kiseki.domain.shared.speed import Speed

JST = timezone(timedelta(hours=9))
BASE = datetime(2025, 5, 3, 9, 0, tzinfo=JST)
PARK = GeoPoint(35.0094, 135.6669)


def after(minutes: float) -> datetime:
    return BASE + timedelta(minutes=minutes)


def observation(
    name: str, minutes: float, latitude_offset: float = 0.0, located: bool = True
) -> PhotoObservation:
    place = GeoPoint(PARK.latitude + latitude_offset, PARK.longitude) if located else None
    return PhotoObservation(PhotoId(name), after(minutes), place)


def ids(names: tuple[PhotoId, ...]) -> tuple[str, ...]:
    return tuple(identifier.value for identifier in names)


class TestEmptyAndTrivialInput:
    def test_no_observations_yields_nothing(self) -> None:
        result = extract_stops([])
        assert result.stops == ()
        assert result.in_transit == ()
        assert result.unlocated == ()

    def test_a_lone_photograph_is_not_a_stay(self) -> None:
        """One photograph proves presence, not that anyone stayed."""
        result = extract_stops([observation("a", 0)])
        assert result.stops == ()
        assert ids(result.in_transit) == ("a",)


class TestFormingAStop:
    def test_three_photographs_in_one_place_form_a_stop(self) -> None:
        result = extract_stops([observation(f"a{i}", i, 0.00001 * i) for i in range(3)])
        assert len(result.stops) == 1
        assert result.stops[0].photograph_count == 3

    def test_two_photographs_over_a_long_enough_period_form_a_stop(self) -> None:
        result = extract_stops([observation("a", 0), observation("b", 20, 0.0002)])
        assert len(result.stops) == 1

    def test_the_centroid_is_the_mean_of_the_photographs(self) -> None:
        result = extract_stops(
            [observation("a", 0, 0.0), observation("b", 10, 0.002), observation("c", 20, 0.001)]
        )
        assert result.stops[0].centroid.latitude == PARK.latitude + 0.001

    def test_the_span_covers_the_first_and_last_photograph(self) -> None:
        result = extract_stops([observation(f"a{i}", i * 10, 0.00001 * i) for i in range(3)])
        span = result.stops[0].time_range
        assert span.start == after(0)
        assert span.end == after(20)


class TestSeparatingMovementFromStaying:
    def test_photographs_taken_while_moving_fast_are_in_transit(self) -> None:
        """Shots from a train window must not become a series of stops."""
        moving = [
            PhotoObservation(
                PhotoId(f"f{i}"),
                after(i * 5),
                GeoPoint(PARK.latitude + 0.05 * i, PARK.longitude),
            )
            for i in range(4)
        ]
        result = extract_stops(moving)
        assert result.stops == ()
        assert len(result.in_transit) == 4

    def test_slow_drift_beyond_the_radius_stays_one_stop(self) -> None:
        """Walking around a large park is still one visit."""
        strolling = [observation(f"w{i}", i * 10, 0.0009 * i) for i in range(8)]
        result = extract_stops(strolling)
        assert len(result.stops) == 1
        assert result.stops[0].photograph_count == 8

    def test_small_jitter_does_not_split_a_stop(self) -> None:
        """Consumer GPS wanders by tens of metres while standing still."""
        jitter = [0.0, 0.0003, -0.0002, 0.0005, 0.0001]
        result = extract_stops(
            [observation(f"j{i}", i * 30, offset) for i, offset in enumerate(jitter)]
        )
        assert len(result.stops) == 1


class TestSplitting:
    def test_a_long_gap_splits_the_day(self) -> None:
        morning = [observation(f"m{i}", i * 10, 0.0001 * i) for i in range(3)]
        afternoon = [observation(f"n{i}", 240 + i * 10, 0.0001 * i) for i in range(3)]
        result = extract_stops(morning + afternoon)
        assert len(result.stops) == 2

    def test_identical_timestamps_far_apart_do_not_merge(self) -> None:
        """Two devices can disagree. A zero gap cannot imply a speed."""
        result = extract_stops(
            [
                observation("a", 0),
                PhotoObservation(PhotoId("b"), after(0), GeoPoint(35.5, 136.0)),
            ]
        )
        assert result.stops == ()
        assert len(result.in_transit) == 2


class TestUnlocatedPhotographs:
    def test_photographs_without_coordinates_are_kept_aside(self) -> None:
        result = extract_stops([observation("x", 0, located=False)])
        assert ids(result.unlocated) == ("x",)
        assert result.stops == ()

    def test_they_do_not_disturb_the_located_ones(self) -> None:
        located = [observation(f"p{i}", i * 10, 0.00001 * i) for i in range(3)]
        result = extract_stops([observation("x", 5, located=False), *located])
        assert len(result.stops) == 1
        assert ids(result.unlocated) == ("x",)

    def test_every_photograph_is_accounted_for(self) -> None:
        """Nothing is silently dropped."""
        given = [
            observation("x", 0, located=False),
            *[observation(f"p{i}", i * 10, 0.00001 * i) for i in range(3)],
            PhotoObservation(PhotoId("far"), after(200), GeoPoint(36.0, 136.0)),
        ]
        result = extract_stops(given)
        seen = {
            identifier.value
            for stop in result.stops
            for identifier in stop.photo_ids
        }
        seen |= {identifier.value for identifier in result.in_transit}
        seen |= {identifier.value for identifier in result.unlocated}
        assert seen == {item.photo_id.value for item in given}


class TestOrdering:
    def test_input_order_does_not_matter(self) -> None:
        shuffled = [observation(f"a{i}", i * 10, 0.00005 * i) for i in (2, 0, 1)]
        result = extract_stops(shuffled)
        assert ids(result.stops[0].photo_ids) == ("a0", "a1", "a2")


class TestSettings:
    def test_a_tighter_radius_and_speed_split_more(self) -> None:
        strolling = [observation(f"w{i}", i * 10, 0.0009 * i) for i in range(4)]
        loose = extract_stops(strolling)
        tight = extract_stops(
            strolling,
            StopSettings(
                stay_radius=Distance(10),
                drift_speed=Speed.from_kilometers_per_hour(0.1),
            ),
        )
        assert len(loose.stops) == 1
        assert len(tight.stops) == 0

    def test_a_shorter_minimum_duration_admits_brief_visits(self) -> None:
        brief = [observation("a", 0), observation("b", 2, 0.0001)]
        assert extract_stops(brief).stops == ()
        assert len(extract_stops(brief, StopSettings(min_duration=timedelta(minutes=1))).stops) == 1

    def test_defaults_are_applied_when_no_settings_are_given(self) -> None:
        assert extract_stops([observation("a", 0)]) == extract_stops(
            [observation("a", 0)], StopSettings()
        )
