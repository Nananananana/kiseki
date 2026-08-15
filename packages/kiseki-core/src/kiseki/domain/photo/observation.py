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

    content_kind: str | None = None
    """What the record said it was: "photo", "screenshot", "document"
    or "other", from PhotoRecord v1. None for records stored before
    the field was carried; by the rules of their time those were
    camera photographs. See ADR-0028."""

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone aware")

    @property
    def is_located(self) -> bool:
        return self.location is not None

    @property
    def joins_journeys(self) -> bool:
        """Whether this observation may shape stops and anchors.

        A screenshot or a saved image has a location -- where the
        device was -- but not one that was chosen, and choice is what
        a journey is made of. Only camera photographs, and legacy
        records that predate the field, take part. See ADR-0028.
        """
        return self.content_kind is None or self.content_kind == "photo"
