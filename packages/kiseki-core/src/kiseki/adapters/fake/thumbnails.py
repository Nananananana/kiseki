"""In-memory thumbnail source, for tests and examples."""

from __future__ import annotations

from kiseki.ports.thumbnails import ThumbnailMissingError


class FakeThumbnailSource:
    """Serves bytes from a dictionary; conforms to ThumbnailSource."""

    def __init__(self, images: dict[str, bytes] | None = None) -> None:
        self._images = dict(images or {})

    def read(self, thumbnail_ref: str) -> bytes:
        try:
            return self._images[thumbnail_ref]
        except KeyError as error:
            raise ThumbnailMissingError(f"no thumbnail at {thumbnail_ref}") from error
