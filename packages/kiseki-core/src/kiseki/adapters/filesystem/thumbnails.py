"""Thumbnails on disk, resolved against the configured root.

A reference that resolves outside the root is refused: references come
from stored data, and stored data must not be able to read arbitrary
files.
"""

from __future__ import annotations

from pathlib import Path

from kiseki.ports.thumbnails import ThumbnailMissingError


class FilesystemThumbnailSource:
    """Joins the thumbnail root and the reference; conforms to ThumbnailSource."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def read(self, thumbnail_ref: str) -> bytes:
        root = self._root.resolve()
        candidate = (root / thumbnail_ref).resolve()
        if not candidate.is_relative_to(root):
            raise ThumbnailMissingError(f"{thumbnail_ref} escapes the thumbnail root")
        try:
            return candidate.read_bytes()
        except OSError as error:
            raise ThumbnailMissingError(f"no thumbnail at {thumbnail_ref}") from error
