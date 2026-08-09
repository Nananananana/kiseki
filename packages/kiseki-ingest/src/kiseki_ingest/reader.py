"""Reading EXIF out of an image file. The only module that touches Pillow."""

from dataclasses import dataclass, field
from pathlib import Path

from PIL import ExifTags, Image

EXIF_IFD = 0x8769
GPS_IFD = 0x8825
_BASE = {name: tag for tag, name in ExifTags.TAGS.items()}
_GPS = {name: tag for tag, name in ExifTags.GPSTAGS.items()}


@dataclass(frozen=True)
class RawExif:
    """EXIF values as read, before interpretation."""

    make: str | None = None
    model: str | None = None
    captured_at: str | None = None
    offset: str | None = None
    gps: dict[str, object] = field(default_factory=dict)
    width: int | None = None
    height: int | None = None

    @property
    def has_camera_metadata(self) -> bool:
        return bool(self.make or self.model)


def read_exif(path: Path) -> RawExif:
    with Image.open(path) as image:
        exif = image.getexif()
        detail = exif.get_ifd(EXIF_IFD)
        gps = exif.get_ifd(GPS_IFD)
        width, height = image.size

        return RawExif(
            make=_text(exif.get(_BASE["Make"])),
            model=_text(exif.get(_BASE["Model"])),
            captured_at=_text(detail.get(_BASE["DateTimeOriginal"])),
            offset=_text(detail.get(_BASE["OffsetTimeOriginal"])),
            gps={
                "latitude": gps.get(_GPS["GPSLatitude"]),
                "latitude_ref": gps.get(_GPS["GPSLatitudeRef"]),
                "longitude": gps.get(_GPS["GPSLongitude"]),
                "longitude_ref": gps.get(_GPS["GPSLongitudeRef"]),
            },
            width=width,
            height=height,
        )


def _text(value: object) -> str | None:
    """EXIF strings arrive padded with nulls and whitespace often enough to matter."""
    if value is None:
        return None
    text = str(value).strip().strip("\x00")
    return text or None
