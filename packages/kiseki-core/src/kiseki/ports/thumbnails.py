"""Port for resolving a thumbnail reference to image bytes.

The domain carries `thumbnail_ref` as an opaque relative reference
(ADR-0018); something outside the domain has to turn it into pixels.
"""

from typing import Protocol


class ThumbnailMissingError(RuntimeError):
    """The reference could not be resolved to an image.

    The file is gone, the reference is malformed, or it points outside
    the thumbnail root. Retrying without re-ingesting will not help,
    so a captioning run records it rather than pausing on it.
    """


class ThumbnailSource(Protocol):
    """Turns a thumbnail reference into the bytes of the image."""

    def read(self, thumbnail_ref: str) -> bytes:
        """Raises ThumbnailMissingError when the reference cannot be resolved."""
        ...
