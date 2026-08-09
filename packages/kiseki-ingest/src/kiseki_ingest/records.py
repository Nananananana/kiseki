"""Turning a file on disk into a PhotoRecord."""

import hashlib
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any

from PIL import Image

from kiseki_ingest.exif import extract_location, parse_captured_at
from kiseki_ingest.reader import RawExif, read_exif

READ_CHUNK = 1024 * 1024
THUMBNAIL_MAX_EDGE = 512
THUMBNAIL_QUALITY = 80


@dataclass(frozen=True)
class Owner:
    owner_id: str
    device_id: str | None = None
    platform: str | None = None

    def as_dict(self) -> dict[str, str]:
        payload: dict[str, str] = {"owner_id": self.owner_id}
        if self.device_id:
            payload["device_id"] = self.device_id
        if self.platform:
            payload["platform"] = self.platform
        return payload


@dataclass(frozen=True)
class Consent:
    use_for_preference: bool
    use_for_story: bool

    def as_dict(self) -> dict[str, bool]:
        return {
            "use_for_preference": self.use_for_preference,
            "use_for_story": self.use_for_story,
        }


@dataclass(frozen=True)
class Skipped:
    path: Path
    reason: str


def hash_file(path: Path) -> str:
    """Content hash, read in chunks so a large library does not need to fit in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(READ_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def classify(raw: RawExif) -> str:
    """Camera metadata is the only signal available at this stage.

    Refining this into screenshot and document detection is issue #9.
    """
    return "photo" if raw.make or raw.model else "other"


def write_thumbnail(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        thumbnail = image.convert("RGB")
        thumbnail.thumbnail((THUMBNAIL_MAX_EDGE, THUMBNAIL_MAX_EDGE))
        thumbnail.save(destination, "JPEG", quality=THUMBNAIL_QUALITY)


def build_record(
    path: Path,
    *,
    owner: Owner,
    consent: Consent,
    default_offset: timezone,
    thumbnail_root: Path,
) -> dict[str, Any]:
    """Build one PhotoRecord and write its thumbnail.

    Raises ValueError when the file carries no capture time. A record without a
    position in time cannot take part in a journey, so it is reported as skipped
    rather than given a guessed timestamp.
    """
    from kiseki_ingest import __version__

    raw = read_exif(path)
    if raw.captured_at is None:
        raise ValueError("no DateTimeOriginal, the record has no position in time")

    captured_at = parse_captured_at(raw.captured_at, raw.offset, default_offset)
    digest = hash_file(path)
    reference = f"{captured_at.year:04d}/{captured_at.month:02d}/{digest[:16]}.jpg"
    write_thumbnail(path, thumbnail_root / reference)

    record: dict[str, Any] = {
        "id": f"sha256:{digest}",
        "captured_at": captured_at.isoformat(),
        "media_type": "image",
        "content_kind": classify(raw),
        "thumbnail_ref": reference,
        "owner": owner.as_dict(),
        "consent": consent.as_dict(),
        "source": {"exporter": "kiseki-ingest", "version": __version__},
    }

    location = extract_location(raw.gps)
    if location is None:
        record["location"] = None
    else:
        latitude, longitude = location
        record["location"] = {"lat": latitude, "lon": longitude}
        record["location_source"] = "measured"
    return record
