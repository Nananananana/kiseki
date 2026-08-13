"""Port for keeping captions.

Captions accumulate. They are never replaced wholesale on a rebuild,
because they cost hours to make and are keyed by photographs rather
than by the derived stops. See ADR-0019.
"""

from typing import Protocol

from kiseki.domain.caption.caption import Caption, CaptionKey


class CaptionRepository(Protocol):
    """Stores captions by key; the store doubles as the progress record."""

    def save(self, caption: Caption) -> None:
        """Keep a caption, replacing any existing one with the same key."""
        ...

    def get(self, key: CaptionKey) -> Caption | None:
        """The caption for these photographs, or None if not yet made."""
        ...

    def all(self) -> tuple[Caption, ...]:
        """Every caption, in the order they were saved."""
        ...
