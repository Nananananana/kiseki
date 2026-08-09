"""Generation of synthetic photographs carrying EXIF metadata.

No real photograph is ever committed to this repository. Tests build exactly the
images they need, in a temporary directory, and throw them away afterwards.
"""

from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image
from PIL.TiffImagePlugin import IFDRational

EXIF_IFD = 0x8769
GPS_IFD = 0x8825
_BASE = {name: tag for tag, name in ExifTags.TAGS.items()}
_GPS = {name: tag for tag, name in ExifTags.GPSTAGS.items()}


def _dms(value: float) -> tuple[IFDRational, IFDRational, IFDRational]:
    magnitude = abs(value)
    degrees = int(magnitude)
    minutes = int((magnitude - degrees) * 60)
    seconds = (magnitude - degrees - minutes / 60) * 3600
    return IFDRational(degrees), IFDRational(minutes), IFDRational(round(seconds * 100), 100)


def write_photo(
    path: Path,
    *,
    captured_at: datetime | None = None,
    offset: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    make: str | None = "Synthetic",
    model: str | None = "Fixture",
    size: tuple[int, int] = (64, 48),
    colour: tuple[int, int, int] = (120, 140, 160),
) -> Path:
    """Write a JPEG with the requested EXIF metadata present or absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", size, colour)
    exif = image.getexif()

    if make:
        exif[_BASE["Make"]] = make
    if model:
        exif[_BASE["Model"]] = model

    if captured_at is not None:
        detail = exif.get_ifd(EXIF_IFD)
        detail[_BASE["DateTimeOriginal"]] = captured_at.strftime("%Y:%m:%d %H:%M:%S")
        if offset:
            detail[_BASE["OffsetTimeOriginal"]] = offset

    if latitude is not None and longitude is not None:
        gps = exif.get_ifd(GPS_IFD)
        gps[_GPS["GPSLatitudeRef"]] = "N" if latitude >= 0 else "S"
        gps[_GPS["GPSLatitude"]] = _dms(latitude)
        gps[_GPS["GPSLongitudeRef"]] = "E" if longitude >= 0 else "W"
        gps[_GPS["GPSLongitude"]] = _dms(longitude)

    image.save(path, "JPEG", exif=exif.tobytes())
    return path


def write_screenshot(path: Path, size: tuple[int, int] = (390, 844)) -> Path:
    """An image with no camera metadata at all, as a screenshot would be."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (20, 20, 24)).save(path, "PNG")
    return path
