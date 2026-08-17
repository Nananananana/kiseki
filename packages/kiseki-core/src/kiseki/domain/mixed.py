"""Two tendencies held side by side, neither one resolved away.

One person is not one profile: an interest that stayed strong and
an interest that grew are both true at once, and KISEKI states
them together instead of flattening them into a category or
calling them a contradiction. See ADR-0049.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MixedPair:
    """One held-together statement, with the numbers behind it."""

    held: str
    held_strength: float
    rising: str
    rising_magnitude: float

    def __post_init__(self) -> None:
        if not self.held or not self.rising:
            raise ValueError("a mixed pair needs both topics")
        if self.held == self.rising:
            raise ValueError("a mixed pair needs two different topics")
        if self.held_strength < 0 or self.rising_magnitude < 0:
            raise ValueError("strengths cannot be negative")
