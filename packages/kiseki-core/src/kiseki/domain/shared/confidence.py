"""How well supported a derived statement is.

Everything this library infers carries one of these. A profile drawn from four
outings and one drawn from four hundred are not the same claim, and the
difference has to survive all the way to the answer the user reads.
"""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, order=True)
class Confidence:
    """A value in the unit interval, with the number of records behind it."""

    value: float
    sample_size: int

    def __post_init__(self) -> None:
        if not isfinite(self.value):
            raise ValueError("confidence must be a finite number")
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"confidence {self.value} is outside [0.0, 1.0]")
        if self.sample_size < 0:
            raise ValueError("sample size cannot be negative")

    @classmethod
    def unknown(cls) -> "Confidence":
        return cls(0.0, 0)

    def is_supported_by(self, minimum_samples: int) -> bool:
        """Whether enough records back this value, regardless of how high it is."""
        return self.sample_size >= minimum_samples
