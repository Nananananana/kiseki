"""Speed derived from a distance and a duration.

Stop extraction decides whether consecutive photos represent a stay or a
journey by comparing the implied speed against a threshold. Expressing that as
a type keeps the comparison honest: a raw float could be metres per second or
kilometres per hour, and the two differ by a factor of 3.6.
"""

from dataclasses import dataclass
from datetime import timedelta
from math import isfinite

from kiseki.domain.shared.geo import Distance

SECONDS_PER_HOUR = 3600


@dataclass(frozen=True, order=True)
class Speed:
    """A non-negative speed."""

    meters_per_second: float

    def __post_init__(self) -> None:
        if not isfinite(self.meters_per_second):
            raise ValueError("speed must be a finite number")
        if self.meters_per_second < 0:
            raise ValueError("speed cannot be negative")

    @property
    def kilometers_per_hour(self) -> float:
        return self.meters_per_second * SECONDS_PER_HOUR / 1000

    @classmethod
    def from_kilometers_per_hour(cls, value: float) -> "Speed":
        return cls(value * 1000 / SECONDS_PER_HOUR)

    @classmethod
    def between(cls, distance: Distance, duration: timedelta) -> "Speed":
        """Speed implied by covering a distance in a duration.

        A zero duration is rejected rather than treated as infinite speed. Two
        photos sharing a timestamp is a data condition for the caller to handle,
        not a physical fact to encode.
        """
        seconds = duration.total_seconds()
        if seconds <= 0:
            raise ValueError("duration must be positive to derive a speed")
        return cls(distance.meters / seconds)
