"""What the owner opened, as the core is willing to receive it.

A reading is keyed by the page and the day, so a page returned to
across months is several readings rather than one that keeps being
corrected (ADR-0076). The implementer never imports this; the port
belongs to the core (ADR-0004).
"""

from collections.abc import Sequence
from typing import Protocol

from kiseki.domain.web.reading import PageReading


class PageReadingRepository(Protocol):
    """Page readings, kept as they arrive."""

    def save(self, reading: PageReading) -> None: ...

    def save_all(self, readings: Sequence[PageReading]) -> None: ...

    def all(self) -> tuple[PageReading, ...]: ...

    def count(self) -> int: ...
