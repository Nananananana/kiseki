"""Specification for outing assembly.

An outing is a run of stops with no long silence between them. Every stop takes
part: a familiar place is still somewhere the person went, and dropping it would
remove the strongest evidence of what they like. See ADR-0012.
"""

from datetime import datetime, timedelta, timezone

from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.services.outing_assembly import assemble_outings
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.settings import OutingSettings
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 5, day, hour, minute, tzinfo=JST)


def stop(name: str, day: int, start: int, end: int, latitude: float, longitude: float) -> Stop:
    return Stop(
        tuple(PhotoId(f"{name}_{day}_{index}") for index in range(3)),
        TimeRange(at(day, start), at(day, end)),
        GeoPoint(latitude, longitude),
    )


def names(outing_stops: tuple[Stop, ...]) -> tuple[str, ...]:
    return tuple(item.photo_ids[0].value.split("_")[0] for item in outing_stops)


HOME_MORNING = stop("home", 3, 7, 8, 35.6813, 139.7670)
PARK = stop("park", 3, 9, 11, 35.0094, 135.6669)
LUNCH = stop("lunch", 3, 12, 13, 35.0150, 135.6780)
MUSEUM = stop("museum", 3, 14, 16, 35.0250, 135.7600)
NEXT_DAY_CAFE = stop("cafe", 4, 10, 11, 35.6600, 139.7000)


class TestEmptyInput:
    def test_nothing_in_nothing_out(self) -> None:
        assert assemble_outings([]) == ()


class TestGrouping:
    def test_a_long_silence_ends_an_outing(self) -> None:
        outings = assemble_outings([PARK, LUNCH, MUSEUM, NEXT_DAY_CAFE])
        assert len(outings) == 2
        assert names(outings[1].stops) == ("cafe",)

    def test_a_short_silence_does_not(self) -> None:
        assert len(assemble_outings([PARK, LUNCH, MUSEUM])) == 1

    def test_input_order_does_not_matter(self) -> None:
        outings = assemble_outings([MUSEUM, PARK, LUNCH])
        assert names(outings[0].stops) == ("park", "lunch", "museum")


class TestNothingIsExcluded:
    def test_a_familiar_place_is_still_part_of_an_outing(self) -> None:
        """Somewhere returned to is evidence of preference, not noise."""
        outings = assemble_outings([HOME_MORNING, PARK, LUNCH, MUSEUM])
        assert len(outings) == 1
        assert names(outings[0].stops) == ("home", "park", "lunch", "museum")

    def test_every_stop_is_accounted_for(self) -> None:
        given = [HOME_MORNING, PARK, LUNCH, MUSEUM, NEXT_DAY_CAFE]
        seen = [stop for outing in assemble_outings(given) for stop in outing.stops]
        assert set(seen) == set(given)
        assert len(seen) == len(given)


class TestSettings:
    def test_a_shorter_tolerance_splits_a_single_day(self) -> None:
        settings = OutingSettings(max_absence=timedelta(minutes=30))
        assert len(assemble_outings([PARK, LUNCH, MUSEUM], settings)) == 3

    def test_a_longer_tolerance_joins_two_days(self) -> None:
        settings = OutingSettings(max_absence=timedelta(days=2))
        assert len(assemble_outings([PARK, LUNCH, MUSEUM, NEXT_DAY_CAFE], settings)) == 1

    def test_defaults_apply_when_none_are_given(self) -> None:
        assert assemble_outings([PARK, LUNCH]) == assemble_outings([PARK, LUNCH], OutingSettings())
