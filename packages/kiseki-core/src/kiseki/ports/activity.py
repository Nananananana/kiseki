"""Days of movement, as the core is willing to receive them.

One row per calendar day, and a day the device did not record is
simply absent -- there is no zero fill and no interpolation, because a
missing day means nobody counted, which is not the same as a day of no
steps. The implementer never imports this; the port belongs to the
core (ADR-0004).
"""

from collections.abc import Sequence
from typing import Protocol

from kiseki.domain.activity.daily import DailyActivity


class DailyActivityRepository(Protocol):
    """Days of movement, kept as they arrive."""

    def save_all(self, days: Sequence[DailyActivity]) -> None: ...

    def all(self) -> tuple[DailyActivity, ...]: ...

    def count(self) -> int: ...
