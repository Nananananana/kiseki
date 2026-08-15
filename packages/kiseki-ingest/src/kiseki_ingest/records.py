"""Turning a file on disk into a PhotoRecord."""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from kiseki_ingest.classification import PHOTO, MediaEvidence, classify
from kiseki_ingest.exif import extract_location, parse_captured_at
from kiseki_ingest.reader import read_exif

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


def write_thumbnail(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        thumbnail = image.convert("RGB")
        thumbnail.thumbnail((THUMBNAIL_MAX_EDGE, THUMBNAIL_MAX_EDGE))
        thumbnail.save(destination, "JPEG", quality=THUMBNAIL_QUALITY)


def _modified_at(path: Path) -> datetime:
    """The file's modified time, in the machine's own zone, offset included."""
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone()


def build_record(
    path: Path,
    *,
    owner: Owner,
    consent: Consent,
    default_offset: timezone,
    thumbnail_root: Path,
    digest: str | None = None,
    mtime_fallback: bool = False,
) -> dict[str, Any]:
    """Build one PhotoRecord and write its thumbnail.

    Raises ValueError when the file carries no capture time. A record
    without a position in time cannot take part in a journey, so it is
    reported as skipped rather than given a guessed timestamp. With
    ``mtime_fallback``, a non-photograph without one borrows the
    file's modified time instead -- a measured filesystem fact, not a
    guess -- and declares it in ``extra.time_source``. A photograph
    without a capture time stays skipped either way: on a camera file
    that absence is an anomaly. See ADR-0029.

    ``digest`` may be supplied by a caller that has already hashed the
    file for duplicate detection, to avoid reading it twice.
    """
    from kiseki_ingest import __version__

    raw = read_exif(path)
    evidence = MediaEvidence(
        filename=path.name,
        suffix=path.suffix,
        has_camera_metadata=raw.has_camera_metadata,
        width=raw.width,
        height=raw.height,
    )
    kind = classify(evidence)

    time_source: str | None = None
    if raw.captured_at is not None:
        captured_at = parse_captured_at(raw.captured_at, raw.offset, default_offset)
    elif mtime_fallback and kind != PHOTO:
        captured_at = _modified_at(path)
        time_source = "file-modified"
    else:
        raise ValueError("no DateTimeOriginal, the record has no position in time")

    content_hash = digest if digest is not None else hash_file(path)
    reference = f"{captured_at.year:04d}/{captured_at.month:02d}/{content_hash[:16]}.jpg"
    write_thumbnail(path, thumbnail_root / reference)

    record: dict[str, Any] = {
        "id": f"sha256:{content_hash}",
        "captured_at": captured_at.isoformat(),
        "media_type": "image",
        "content_kind": kind,
        "thumbnail_ref": reference,
        "owner": owner.as_dict(),
        "consent": consent.as_dict(),
        "source": {"exporter": "kiseki-ingest", "version": __version__},
    }
    if time_source is not None:
        record["extra"] = {"time_source": time_source}

    location = extract_location(raw.gps)
    if location is None:
        record["location"] = None
    else:
        latitude, longitude = location
        record["location"] = {"lat": latitude, "lon": longitude}
        record["location_source"] = "measured"
    return record
