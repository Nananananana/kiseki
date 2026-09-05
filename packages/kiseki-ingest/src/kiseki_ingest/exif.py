"""Interpretation of EXIF values.

Pure functions. No file access, no imaging library, so every rule here is
testable in microseconds and independent of what Pillow happens to return.
"""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta, timezone
from typing import SupportsFloat, cast

EXIF_DATETIME_FORMAT = "%Y:%m:%d %H:%M:%S"
GPS_KEYS = ("latitude", "latitude_ref", "longitude", "longitude_ref")


def parse_offset(raw: str) -> timezone:
    """Interpret an EXIF OffsetTimeOriginal value such as ``+09:00``."""
    text = raw.strip()
    if text in {"Z", "+00:00", "-00:00"}:
        return UTC
    if len(text) != 6 or text[0] not in "+-" or text[3] != ":":
        raise ValueError(f"{raw!r} is not a valid UTC offset")
    sign = 1 if text[0] == "+" else -1
    hours, minutes = int(text[1:3]), int(text[4:6])
    if hours > 23 or minutes > 59:
        raise ValueError(f"{raw!r} is not a valid UTC offset")
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def parse_captured_at(raw: str, offset: str | None, fallback: timezone) -> datetime:
    """Combine DateTimeOriginal with an offset.

    Cameras and older phones frequently omit OffsetTimeOriginal. The contract
    requires an offset, so the caller must supply one to fall back on rather
    than letting a naive timestamp through.
    """
    naive = datetime.strptime(raw.strip(), EXIF_DATETIME_FORMAT)  # noqa: DTZ007 -- the zone is attached two lines down
    zone = parse_offset(offset) if offset else fallback
    return naive.replace(tzinfo=zone)


def _to_float(value: object) -> float:
    """Accept either a rational tuple or an object that converts to a float.

    EXIF stores GPS components as rationals. Pillow hands them back as
    IFDRational, other readers as a plain (numerator, denominator) pair, and
    some as a bare number. All three occur in real files.
    """
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError(f"{value!r} is not a rational number")
        numerator, denominator = (_to_float(part) for part in value)
        if denominator == 0:
            raise ValueError("a rational number cannot have a zero denominator")
        return numerator / denominator
    if isinstance(value, SupportsFloat):
        return float(value)
    raise ValueError(f"{value!r} is not a number")


def _to_degrees(values: Sequence[object]) -> float:
    if len(values) != 3:
        raise ValueError("a GPS coordinate needs degrees, minutes and seconds")
    degrees, minutes, seconds = (_to_float(value) for value in values)
    return degrees + minutes / 60 + seconds / 3600


def parse_coordinate(values: Sequence[object], reference: str) -> float:
    """Convert degrees, minutes and seconds plus a hemisphere into a signed value."""
    magnitude = _to_degrees(values)
    ref = reference.strip().upper()
    if ref in {"S", "W"}:
        return -magnitude
    if ref in {"N", "E"}:
        return magnitude
    raise ValueError(f"{reference!r} is not a valid hemisphere reference")


def extract_location(gps: Mapping[str, object]) -> tuple[float, float] | None:
    """Return coordinates, or None when the photo carries no usable GPS data."""
    if not all(gps.get(key) for key in GPS_KEYS):
        return None

    latitude = parse_coordinate(cast(Sequence[object], gps["latitude"]), str(gps["latitude_ref"]))
    longitude = parse_coordinate(
        cast(Sequence[object], gps["longitude"]), str(gps["longitude_ref"])
    )

    if not -90 <= latitude <= 90:
        raise ValueError(f"latitude {latitude} is outside [-90, 90]")
    if not -180 <= longitude <= 180:
        raise ValueError(f"longitude {longitude} is outside [-180, 180]")
    return latitude, longitude
