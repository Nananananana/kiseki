"""One departure from an anchor and return to it."""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from kiseki.domain.outing.stop import Stop
from kiseki.domain.shared.geo import Distance
from kiseki.domain.shared.time_range import TimeRange

IDENTIFIER_LENGTH = 16


@dataclass(frozen=True)
class OutingId:
    """Derived from the photographs an outing contains.

    Outings are not edited; they are recomputed from scratch whenever the
    library runs. A content derived identifier therefore stays stable across
    runs, and changes exactly when the outing itself is a different outing.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("an outing id cannot be empty")

    @classmethod
    def derive(cls, stops: Sequence[Stop]) -> "OutingId":
        joined = "|".join(
            sorted(identifier.value for stop in stops for identifier in stop.photo_ids)
        )
        digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
        return cls(digest[:IDENTIFIER_LENGTH])


@dataclass(frozen=True)
class Outing:
    """An ordered sequence of stops away from any anchor."""

    id: OutingId
    stops: tuple[Stop, ...]

    def __post_init__(self) -> None:
        if not self.stops:
            raise ValueError("an outing needs at least one stop")

    @classmethod
    def of(cls, stops: Sequence[Stop]) -> "Outing":
        """Build an outing, ordering the stops and deriving the identifier."""
        ordered = tuple(sorted(stops, key=lambda stop: stop.time_range.start))
        return cls(OutingId.derive(ordered), ordered)

    @property
    def time_range(self) -> TimeRange:
        return TimeRange(self.stops[0].time_range.start, self.stops[-1].time_range.end)

    @property
    def duration(self) -> timedelta:
        return self.time_range.duration

    @property
    def stop_count(self) -> int:
        return len(self.stops)

    @property
    def photograph_count(self) -> int:
        return sum(stop.photograph_count for stop in self.stops)

    @property
    def travelled(self) -> Distance:
        """Distance between consecutive stops, ignoring the route actually taken."""
        legs = zip(self.stops, self.stops[1:], strict=False)
        return Distance(
            sum(first.centroid.distance_to(second.centroid).meters for first, second in legs)
        )
