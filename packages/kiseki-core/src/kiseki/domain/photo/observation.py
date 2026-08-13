"""What the domain knows about a single photograph.

The domain does not read files, thumbnails or EXIF. It works with the time and
place a photograph was taken, and references to refer back to it: the photo id
names the photograph, and the thumbnail reference names a reduced copy of it,
relative to a root the domain knows nothing about. Both are opaque here; an
adapter resolves them. See ADR-0018.
"""

from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.shared.geo import GeoPoint


@dataclass(frozen=True)
class PhotoId:
    """A reference to a photograph. Opaque to the domain."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("a photo id cannot be empty")


@dataclass(frozen=True)
class PhotoObservation:
    """A photograph reduced to when and where it was taken."""

    photo_id: PhotoId
    captured_at: datetime
    location: GeoPoint | None = None
    thumbnail_ref: str | None = None
    """Relative reference to a reduced copy of the image, from
    PhotoRecord v1. None for records stored before the field was
    carried; such photographs cannot be captioned, and nothing else
    about them changes."""

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone aware")

    @property
    def is_located(self) -> bool:
        return self.location is not None
