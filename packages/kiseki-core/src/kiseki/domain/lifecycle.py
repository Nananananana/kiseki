"""Where a topic stands in its life.

A lifecycle is derived from the whole kept profile history and never
stored -- the decision proposals/0001 made before there was anything
to label. See ADR-0042.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique

from kiseki.domain.shared.moment import naive


@unique
class LifecycleStage(Enum):
    """The stages a topic can be read as being in."""

    NEW = "new"
    RETURNED = "returned"
    GROWING = "growing"
    DECLINING = "declining"
    DORMANT = "dormant"
    STABLE = "stable"


@dataclass(frozen=True)
class TopicLifecycle:
    """One topic's stage, with the little arithmetic behind it."""

    topic: str
    stage: LifecycleStage
    strength: float
    seen_profiles: int
    baseline: float = 0.0

    def __post_init__(self) -> None:
        if not self.topic:
            raise ValueError("a lifecycle needs a topic")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("strength must lie within [0, 1]")
        if self.seen_profiles < 1:
            raise ValueError("a topic must have appeared at least once")
        if self.baseline < 0:
            raise ValueError("a baseline cannot be negative")


@dataclass(frozen=True)
class LifecycleReport:
    """Every topic's stage, the interesting ones first."""

    oldest_at: datetime
    latest_at: datetime
    lifecycles: tuple[TopicLifecycle, ...]

    def __post_init__(self) -> None:
        if naive(self.oldest_at) > naive(self.latest_at):
            raise ValueError("the oldest reading cannot follow the latest")
