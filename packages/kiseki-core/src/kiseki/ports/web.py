"""What the owner opened, as the core is willing to receive it.

A reading is keyed by the page and the day, so a page returned to
across months is several readings rather than one that keeps being
corrected (ADR-0076). The implementer never imports this; the port
belongs to the core (ADR-0004).
"""

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from kiseki.domain.web.reading import PageReading


class PageReadingRepository(Protocol):
    """Page readings, kept as they arrive."""

    def save(self, reading: PageReading) -> None: ...

    def save_all(self, readings: Sequence[PageReading]) -> None: ...

    def all(self) -> tuple[PageReading, ...]: ...

    def count(self) -> int: ...

    def remove_all(self, keys: Sequence[tuple[str, date]]) -> int:
        """Remove exactly these (reference, day) readings; how many went.

        The unit is the file the producer wrote: what `kiseki web` took in,
        `kiseki web --withdraw` takes back, key by key. Nothing here removes
        by day range, because a removal that does not know the reference
        cannot say what it removed."""
        ...
