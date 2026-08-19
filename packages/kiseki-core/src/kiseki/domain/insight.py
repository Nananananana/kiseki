"""A finding about the owner: what it is, and what it rests on.

An insight is derived, never invented: raw evidence -> measures,
profile and trend -> deterministic derivation -> insight -> and only
then narration. The model cannot create one. Nothing here is stored;
like the trend and the lifecycle, an insight is recomputed on
demand. See ADR-0043.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique

from kiseki.domain.shared.moment import naive


@unique
class InsightKind(Enum):
    """The findings the derivation knows how to make."""

    NEW = "new"
    RETURNED = "returned"
    RISING = "rising"
    DECLINING = "declining"
    DORMANT = "dormant"
    ENDURING = "enduring"


@unique
class InsightDirection(Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


@dataclass(frozen=True)
class Insight:
    """One deterministic finding, traceable to its evidence."""

    topic: str
    kind: InsightKind
    direction: InsightDirection
    magnitude: float
    first_seen: datetime | None
    last_seen: datetime | None
    confidence: float
    evidence: tuple[str, ...]
    novelty: float
    derived_from: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.topic:
            raise ValueError("an insight needs a topic")
        if self.magnitude < 0:
            raise ValueError("magnitude cannot be negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must lie within [0, 1]")
        if not 0.0 < self.novelty <= 1.0:
            raise ValueError("novelty must lie within (0, 1]")
        if not self.derived_from:
            raise ValueError("an insight must name what it was derived from")
        if self.first_seen and self.last_seen and naive(self.first_seen) > naive(self.last_seen):
            raise ValueError("first_seen cannot follow last_seen")


@dataclass(frozen=True)
class InsightReport:
    """Every current finding, the most novel first."""

    oldest_at: datetime
    latest_at: datetime
    insights: tuple[Insight, ...]

    def __post_init__(self) -> None:
        if naive(self.oldest_at) > naive(self.latest_at):
            raise ValueError("the oldest reading cannot follow the latest")
