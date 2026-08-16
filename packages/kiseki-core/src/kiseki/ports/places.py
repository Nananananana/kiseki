"""Port for naming a place, offline.

Names are resolved at presentation time and never stored: interests
keep their place references, and the gazetteer file can be swapped or
deleted without touching any data. Anchors are never named at all --
naming home would undo what coordinate blurring protects. See
ADR-0040.
"""

from dataclasses import dataclass
from typing import Protocol

from kiseki.domain.shared.geo import Distance, GeoPoint


@dataclass(frozen=True)
class PlaceName:
    """What somewhere is called.

    GeoNames admin columns carry opaque codes, so a name travels with
    its country code only.
    """

    name: str
    country: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a place name cannot be empty")

    @property
    def label(self) -> str:
        return f"{self.name} ({self.country})" if self.country else self.name


class Gazetteer(Protocol):
    """Answers what the nearest named place is, if any is close enough."""

    def nearest(self, point: GeoPoint, within: Distance) -> PlaceName | None:
        """The closest entry within the distance, or None."""
        ...
