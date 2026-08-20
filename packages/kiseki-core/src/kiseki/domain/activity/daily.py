"""A day's worth of moving, counted and nothing more.

The least sensitive thing a phone knows about a body: how many steps
it took today. No positions, no times of day, no route -- a number per
calendar day, exported by the owner from their own device.

It is here for two reasons beyond itself. It proves the record
contract can hold a number as well as a label, which every source
after this one will need. And it meets the derivations the library
already has: a trip with twenty thousand steps a day was a different
trip from one with two thousand, and until now nothing could say so.

What it is not: a health record. Steps are a count of steps. Sleep,
heart rate and weight are symptoms, and this library is not a place to
interpret one (proposals/0008). See ADR-0065.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

MAX_PLAUSIBLE_STEPS = 200_000
"""Beyond this a number is a fault in the export rather than a day.
The ceiling is deliberately absurd: the library refuses the impossible
and never argues with the merely unusual."""


@dataclass(frozen=True)
class DailyActivity:
    """One day of movement, as the owner's own device counted it."""

    day: date
    steps: int
    distance_m: float | None = None
    floors: int | None = None

    def __post_init__(self) -> None:
        if self.steps < 0:
            raise ValueError("a day cannot have fewer than no steps")
        if self.steps > MAX_PLAUSIBLE_STEPS:
            raise ValueError("that is not a day of walking; check the export")
        if self.distance_m is not None and self.distance_m < 0:
            raise ValueError("a distance cannot be negative")
        if self.floors is not None and self.floors < 0:
            raise ValueError("a count of floors cannot be negative")

    @property
    def distance_km(self) -> float | None:
        if self.distance_m is None:
            return None
        return self.distance_m / 1000.0
