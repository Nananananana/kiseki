"""Storage ports.

Declared as protocols rather than base classes, so that an implementation never
has to import this library. Anyone can supply storage by writing a class with
matching methods. See ADR-0004.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.outing.outing import Outing
from kiseki.domain.photo.observation import PhotoObservation


class PhotoRepository(Protocol):
    """Photographs accumulate; they are added to, never replaced wholesale."""

    def save_all(self, observations: Sequence[PhotoObservation]) -> int:
        """Store these, overwriting any with the same identifier. Returns the count."""
        ...

    def all(self) -> tuple[PhotoObservation, ...]:
        """Every photograph, in time order."""
        ...

    def between(self, start: datetime, end: datetime) -> tuple[PhotoObservation, ...]:
        """Photographs captured within the window, inclusive, in time order."""
        ...

    def count(self) -> int: ...


class OutingRepository(Protocol):
    """Outings are derived, so they are replaced rather than amended.

    Adding one photograph can change the shape of the outings around it, which
    makes a wholesale replacement both simpler and more honest than trying to
    patch what is already stored.
    """

    def replace_all(self, outings: Sequence[Outing]) -> int: ...

    def all(self) -> tuple[Outing, ...]:
        """Every outing, earliest first."""
        ...


class AnchorRepository(Protocol):
    """Anchors are derived, and replaced for the same reason as outings."""

    def replace_all(self, anchors: Sequence[Anchor]) -> int: ...

    def all(self) -> tuple[Anchor, ...]:
        """Every anchor, most visited first."""
        ...
