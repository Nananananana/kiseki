"""Ports for reading screenshots and keeping the readings.

The reader is deliberately swappable (ADR-0030): the first adapter is
a VLM prompt, and a dedicated extraction engine can replace it behind
the same protocol when accuracy demands it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.ports.models import Usage


@dataclass(frozen=True)
class ScreenRead:
    """What a reader found on one screen: a category and labels only."""

    category: str
    labels: tuple[str, ...]
    model: str


class ScreenshotReader(Protocol):
    """Reads screenshots into categories and labels."""

    def read(self, images: Sequence[bytes]) -> list[ScreenRead]:
        """One result per image, in the order given.

        Raises ModelUnavailableError if the model could not be
        reached, and ModelRefusedError if it declined or answered
        unusably.
        """
        ...

    @property
    def usage(self) -> Usage: ...


class ScreenshotReadingRepository(Protocol):
    """Stores readings keyed by the photograph they read."""

    def save(self, reading: ScreenshotReading) -> None: ...

    def get(self, photo_id: PhotoId) -> ScreenshotReading | None: ...

    def all(self) -> tuple[ScreenshotReading, ...]: ...
