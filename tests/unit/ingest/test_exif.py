"""Specification for EXIF interpretation."""

from datetime import UTC, timedelta, timezone

import pytest
from kiseki_ingest.exif import (
    extract_location,
    parse_captured_at,
    parse_coordinate,
    parse_offset,
)

JST = timezone(timedelta(hours=9))
KYOTO_LATITUDE = ((35, 1), (0, 1), (3384, 100))
KYOTO_LONGITUDE = ((135, 1), (40, 1), (848, 100))


class TestParseOffset:
    def test_reads_a_positive_offset(self) -> None:
        assert parse_offset("+09:00").utcoffset(None) == timedelta(hours=9)

    def test_reads_a_negative_offset_with_minutes(self) -> None:
        assert parse_offset("-05:30").utcoffset(None) == -timedelta(hours=5, minutes=30)

    def test_reads_zulu_as_utc(self) -> None:
        assert parse_offset("Z") is UTC

    @pytest.mark.parametrize("raw", ["0900", "+9:00", "+09-00", ""])
    def test_rejects_a_malformed_offset(self, raw: str) -> None:
        with pytest.raises(ValueError, match="offset"):
            parse_offset(raw)

    @pytest.mark.parametrize("raw", ["+25:00", "+09:60"])
    def test_rejects_an_impossible_offset(self, raw: str) -> None:
        with pytest.raises(ValueError, match="offset"):
            parse_offset(raw)


class TestParseCapturedAt:
    def test_uses_the_offset_from_the_photo(self) -> None:
        moment = parse_captured_at("2025:05:03 10:24:31", "+09:00", UTC)
        assert moment.isoformat() == "2025-05-03T10:24:31+09:00"

    def test_falls_back_when_the_photo_has_no_offset(self) -> None:
        """Cameras and older phones often omit OffsetTimeOriginal."""
        moment = parse_captured_at("2025:05:03 10:24:31", None, JST)
        assert moment.isoformat() == "2025-05-03T10:24:31+09:00"

    def test_always_returns_an_aware_datetime(self) -> None:
        assert parse_captured_at("2025:05:03 10:24:31", None, JST).tzinfo is not None

    def test_rejects_an_unexpected_format(self) -> None:
        with pytest.raises(ValueError):
            parse_captured_at("2025-05-03 10:24:31", None, JST)


class TestParseCoordinate:
    def test_converts_degrees_minutes_seconds(self) -> None:
        assert parse_coordinate(KYOTO_LATITUDE, "N") == pytest.approx(35.0094, abs=1e-4)

    def test_southern_hemisphere_is_negative(self) -> None:
        assert parse_coordinate(KYOTO_LATITUDE, "S") == pytest.approx(-35.0094, abs=1e-4)

    def test_western_hemisphere_is_negative(self) -> None:
        assert parse_coordinate(KYOTO_LONGITUDE, "W") < 0

    def test_accepts_a_lowercase_reference(self) -> None:
        assert parse_coordinate(KYOTO_LATITUDE, "n") > 0

    def test_rejects_an_unknown_reference(self) -> None:
        with pytest.raises(ValueError, match="hemisphere"):
            parse_coordinate(KYOTO_LATITUDE, "X")

    def test_rejects_an_incomplete_coordinate(self) -> None:
        with pytest.raises(ValueError, match="degrees"):
            parse_coordinate(((35, 1),), "N")


class TestExtractLocation:
    def test_returns_coordinates_when_everything_is_present(self) -> None:
        gps = {
            "latitude": KYOTO_LATITUDE,
            "latitude_ref": "N",
            "longitude": KYOTO_LONGITUDE,
            "longitude_ref": "E",
        }
        latitude, longitude = extract_location(gps)  # type: ignore[misc]
        assert latitude == pytest.approx(35.0094, abs=1e-4)
        assert longitude == pytest.approx(135.669, abs=1e-3)

    def test_returns_none_when_gps_is_absent(self) -> None:
        assert extract_location({}) is None

    def test_returns_none_when_gps_is_partial(self) -> None:
        """A latitude without a hemisphere is unusable, not half usable."""
        assert extract_location({"latitude": KYOTO_LATITUDE}) is None

    def test_rejects_an_impossible_latitude(self) -> None:
        gps = {
            "latitude": ((135, 1), (0, 1), (0, 1)),
            "latitude_ref": "N",
            "longitude": KYOTO_LONGITUDE,
            "longitude_ref": "E",
        }
        with pytest.raises(ValueError, match="latitude"):
            extract_location(gps)
