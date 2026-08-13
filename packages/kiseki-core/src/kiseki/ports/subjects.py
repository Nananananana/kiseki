"""Port for keeping subject readings.

Readings accumulate like captions do: keyed by the caption they read,
never replaced wholesale. See ADR-0020.
"""

from typing import Protocol

from kiseki.domain.caption.caption import CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction


class SubjectRepository(Protocol):
    """Stores readings by caption key; the store doubles as progress."""

    def save(self, reading: SubjectExtraction) -> None:
        """Keep a reading, replacing any existing one with the same key."""
        ...

    def get(self, key: CaptionKey) -> SubjectExtraction | None:
        """The reading for this caption, or None if not yet made."""
        ...

    def all(self) -> tuple[SubjectExtraction, ...]:
        """Every reading, in the order they were saved."""
        ...
