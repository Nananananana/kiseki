"""How the interests moved between two readings.

A trend is an interpretation of interpretations: it compares two kept
profiles and says which topics rose, declined, appeared or faded.
Like every interpretation in this library it is derived, never
stored; it is recomputed from the profile history whenever asked.
See ADR-0025.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique


@unique
class TrendDirection(Enum):
    """Which way a topic moved between the baseline and the latest."""

    NEW = "new"
    RISING = "rising"
    STEADY = "steady"
    DECLINING = "declining"
    FADED = "faded"


@dataclass(frozen=True)
class TopicTrend:
    """One topic's movement between two readings.

    Strength is score x confidence: how strongly the evidence points
    at the topic, discounted by how far the reading can be trusted.
    A faded topic has strength zero; a new one, baseline zero.
    """

    topic: str
    direction: TrendDirection
    strength: float
    baseline: float

    def __post_init__(self) -> None:
        if not self.topic:
            raise ValueError("a trend needs a topic")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("strength must lie within [0, 1]")
        if not 0.0 <= self.baseline <= 1.0:
            raise ValueError("baseline must lie within [0, 1]")

    @property
    def delta(self) -> float:
        """How far the topic moved; negative when it weakened."""
        return self.strength - self.baseline


@dataclass(frozen=True)
class TrendReport:
    """Every movement read between two profiles, largest first."""

    baseline_at: datetime
    latest_at: datetime
    trends: tuple[TopicTrend, ...]

    def __post_init__(self) -> None:
        if self.baseline_at >= self.latest_at:
            raise ValueError("the baseline must precede the latest reading")
