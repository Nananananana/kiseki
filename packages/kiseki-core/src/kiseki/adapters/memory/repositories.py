"""In-memory repositories.

Used by tests and by anyone wanting to run the pipeline without a database.
They are held to the same contract suite as the SQLite implementation, so they
cannot quietly drift from it.
"""

from collections.abc import Sequence
from datetime import datetime

from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.outing.outing import Outing
from kiseki.domain.photo.observation import PhotoId, PhotoObservation


class InMemoryPhotoRepository:
    def __init__(self) -> None:
        self._observations: dict[PhotoId, PhotoObservation] = {}

    def save_all(self, observations: Sequence[PhotoObservation]) -> int:
        for item in observations:
            self._observations[item.photo_id] = item
        return len(observations)

    def all(self) -> tuple[PhotoObservation, ...]:
        return tuple(sorted(self._observations.values(), key=lambda item: item.captured_at))

    def between(self, start: datetime, end: datetime) -> tuple[PhotoObservation, ...]:
        return tuple(item for item in self.all() if start <= item.captured_at <= end)

    def count(self) -> int:
        return len(self._observations)


class InMemoryOutingRepository:
    def __init__(self) -> None:
        self._outings: tuple[Outing, ...] = ()

    def replace_all(self, outings: Sequence[Outing]) -> int:
        self._outings = tuple(sorted(outings, key=lambda outing: outing.time_range.start))
        return len(self._outings)

    def all(self) -> tuple[Outing, ...]:
        return self._outings


class InMemoryAnchorRepository:
    def __init__(self) -> None:
        self._anchors: tuple[Anchor, ...] = ()

    def replace_all(self, anchors: Sequence[Anchor]) -> int:
        self._anchors = tuple(sorted(anchors, key=lambda anchor: anchor.visit_days, reverse=True))
        return len(self._anchors)

    def all(self) -> tuple[Anchor, ...]:
        return self._anchors
