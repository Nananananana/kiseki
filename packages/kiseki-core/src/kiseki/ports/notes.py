"""What the owner wrote, as the core is willing to receive it.

A reading is keyed by the note and the day, so a note returned to
across months is several readings rather than one that keeps being
corrected (ADR-0076). The implementer never imports this; the port
belongs to the core (ADR-0004).
"""

from collections.abc import Sequence
from typing import Protocol

from kiseki.domain.note.reading import NoteReading


class NoteReadingRepository(Protocol):
    """Note readings, kept as they arrive."""

    def save(self, reading: NoteReading) -> None: ...

    def save_all(self, readings: Sequence[NoteReading]) -> None: ...

    def all(self) -> tuple[NoteReading, ...]: ...

    def count(self) -> int: ...
