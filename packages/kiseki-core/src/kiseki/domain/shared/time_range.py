"""A span of time.

Every datetime crossing this boundary must carry a UTC offset. Photos arrive
from devices in different zones, and a naive timestamp cannot be ordered
against one from another device. Ordering is the premise of this library, so a
naive value is rejected rather than assumed to be local.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

NO_GAP = timedelta(0)


@dataclass(frozen=True)
class TimeRange:
    """An inclusive span between two instants. A zero length span is valid."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("TimeRange requires timezone aware datetimes")
        if self.end < self.start:
            raise ValueError("TimeRange cannot end before it starts")

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    def contains(self, moment: datetime) -> bool:
        if moment.tzinfo is None:
            raise ValueError("moment must be timezone aware")
        return self.start <= moment <= self.end

    def overlaps(self, other: "TimeRange") -> bool:
        return self.start <= other.end and other.start <= self.end

    def gap_to(self, other: "TimeRange") -> timedelta:
        """Distance in time between two spans, in either direction. Never negative."""
        if self.overlaps(other):
            return NO_GAP
        if self.end < other.start:
            return other.start - self.end
        return self.start - other.end

    @classmethod
    def spanning(cls, moments: Iterable[datetime]) -> "TimeRange":
        """The smallest range covering every given moment."""
        ordered = sorted(moments)
        if not ordered:
            raise ValueError("cannot span an empty sequence of moments")
        return cls(ordered[0], ordered[-1])
