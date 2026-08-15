"""Port for keeping single-photo captions.

Single captions accumulate like stay captions do: keyed by the
photograph, never replaced wholesale. See ADR-0033.
"""

from typing import Protocol

from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.photo.observation import PhotoId


class SingleCaptionRepository(Protocol):
    """Stores captions by photo id; the store doubles as progress."""

    def save(self, caption: SingleCaption) -> None:
        """Keep a caption, replacing any existing one for the same photograph."""
        ...

    def get(self, photo_id: PhotoId) -> SingleCaption | None:
        """The caption for this photograph, or None if not yet made."""
        ...

    def all(self) -> tuple[SingleCaption, ...]:
        """Every caption, in the order they were saved."""
        ...
