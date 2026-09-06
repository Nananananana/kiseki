"""A day at the keys, as the core is willing to receive it.

One row per calendar day, replaced when the day is read again --
a day is a state, not a thing returned to, which is why this is
keyed like `DailyActivity` and unlike a note or a page (ADR-0076).
The implementer never imports this; the port belongs to the core
(ADR-0004).
"""

from collections.abc import Sequence
from typing import Protocol

from kiseki.domain.input.daily import DailyInput


class DailyInputRepository(Protocol):
    """Days at the keys, kept as they arrive."""

    def save_all(self, days: Sequence[DailyInput]) -> None: ...

    def all(self) -> tuple[DailyInput, ...]: ...

    def count(self) -> int: ...
