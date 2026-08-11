"""Specification for outing assembly.

An outing is one departure from an anchor and return to it. When no anchor is
known yet, the only remaining evidence is how long the silences are.
"""

from datetime import datetime, timedelta, timezone

from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.services.outing_assembly import assemble_outings
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.settings import OutingSettings
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))
HOME = GeoArea(GeoPoint(35.6812, 139.7671), Distance(800))


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2025, 5, day, hour, minute, tzinfo=JST)


def stop(
    name: str, day: int, start: int, end: int, latitude: float, longitude: float
) -> Stop:
    return Stop(
        tuple(PhotoId(f"{name}{index}") for index in range(3)),
        TimeRange(at(day, start), at(day, end)),
        GeoPoint(latitude, longitude),
    )


def names(outing_stops: tuple[Stop, ...]) -> tuple[str, ...]:
    return tuple(stop.photo_ids[0].value.rstrip("0123456789") for stop in outing_stops)


HOME_MORNING = stop("home_am", 3, 7, 8, 35.6813, 139.7670)
HOME_EVENING = stop("home_pm", 3, 19, 20, 35.6810, 139.7675)
PARK = stop("park", 3, 9, 11, 35.0094, 135.6669)
LUNCH = stop("lunch", 3, 12, 13, 35.0150, 135.6780)
MUSEUM = stop("museum", 3, 14, 16, 35.0250, 135.7600)
NEXT_DAY_CAFE = stop("cafe", 4, 10, 11, 35.6600, 139.7000)


class TestEmptyInput:
    def test_nothing_in_nothing_out(self) -> None:
        result = assemble_outings([])
        assert result.outings == ()
        assert result.at_anchor == ()


class TestWithAnchors:
    def test_stops_at_an_anchor_delimit_an_outing(self) -> None:
        result = assemble_outings(
            [HOME_MORNING, PARK, LUNCH, MUSEUM, HOME_EVENING], [HOME]
        )
        assert len(result.outings) == 1
        assert names(result.outings[0].stops) == ("park", "lunch", "museum")

    def test_stops_at_an_anchor_are_reported_separately(self) -> None:
        result = assemble_outings([HOME_MORNING, PARK, HOME_EVENING], [HOME])
        assert names(result.at_anchor) == ("home_am", "home_pm")

    def test_returning_home_starts_a_new_outing(self) -> None:
        """Going out again after coming home is a second outing, not a continuation."""
        errand = stop("errand", 3, 21, 22, 35.5000, 139.5000)
        result = assemble_outings([PARK, HOME_EVENING, errand], [HOME])
        assert len(result.outings) == 2

    def test_several_anchors_are_honoured(self) -> None:
        """A second base, such as a family home, is an anchor too."""
        second = GeoArea(GeoPoint(35.0094, 135.6669), Distance(500))
        result = assemble_outings([PARK, LUNCH], [HOME, second])
        assert names(result.at_anchor) == ("park",)
        assert names(result.outings[0].stops) == ("lunch",)


class TestWithoutAnchors:
    def test_a_long_silence_ends_an_outing(self) -> None:
        result = assemble_outings([PARK, LUNCH, MUSEUM, NEXT_DAY_CAFE])
        assert len(result.outings) == 2
        assert names(result.outings[1].stops) == ("cafe",)

    def test_a_short_silence_does_not(self) -> None:
        result = assemble_outings([PARK, LUNCH, MUSEUM])
        assert len(result.outings) == 1

    def test_nothing_is_reported_at_an_anchor(self) -> None:
        assert assemble_outings([PARK, LUNCH]).at_anchor == ()


class TestOrderingAndCompleteness:
    def test_input_order_does_not_matter(self) -> None:
        result = assemble_outings([MUSEUM, PARK, LUNCH])
        assert names(result.outings[0].stops) == ("park", "lunch", "museum")

    def test_every_stop_is_accounted_for(self) -> None:
        given = [HOME_MORNING, PARK, LUNCH, MUSEUM, HOME_EVENING, NEXT_DAY_CAFE]
        result = assemble_outings(given, [HOME])
        seen = [stop for outing in result.outings for stop in outing.stops]
        seen.extend(result.at_anchor)
        assert len(seen) == len(given)
        assert set(seen) == set(given)


class TestSettings:
    def test_a_shorter_tolerance_splits_a_single_day(self) -> None:
        settings = OutingSettings(max_absence=timedelta(minutes=30))
        result = assemble_outings([PARK, LUNCH, MUSEUM], settings=settings)
        assert len(result.outings) == 3

    def test_a_longer_tolerance_joins_two_days(self) -> None:
        settings = OutingSettings(max_absence=timedelta(days=2))
        result = assemble_outings([PARK, LUNCH, MUSEUM, NEXT_DAY_CAFE], settings=settings)
        assert len(result.outings) == 1

    def test_defaults_apply_when_none_are_given(self) -> None:
        assert assemble_outings([PARK, LUNCH]) == assemble_outings(
            [PARK, LUNCH], settings=OutingSettings()
        )
