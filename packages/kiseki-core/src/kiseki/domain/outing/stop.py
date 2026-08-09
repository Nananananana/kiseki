"""A stay at one place."""

from dataclasses import dataclass
from datetime import timedelta

from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange


@dataclass(frozen=True)
class Stop:
    """One stay, made of the photographs taken during it.

    Photographs are referenced by identifier rather than held directly, because
    they belong to another aggregate.
    """

    photo_ids: tuple[PhotoId, ...]
    time_range: TimeRange
    centroid: GeoPoint

    def __post_init__(self) -> None:
        if not self.photo_ids:
            raise ValueError("a stop needs at least one photograph")
        if len(set(self.photo_ids)) != len(self.photo_ids):
            raise ValueError("a stop cannot list a duplicate photograph")

    @property
    def photograph_count(self) -> int:
        return len(self.photo_ids)

    @property
    def duration(self) -> timedelta:
        return self.time_range.duration
