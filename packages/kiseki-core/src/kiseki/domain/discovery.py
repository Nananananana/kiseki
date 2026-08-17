"""What is worth a look right now, ranked by novelty and importance.

Confidence never ranks the feed, and similarity never enters it
(proposals/0006): confidence says how strongly the evidence
supports a finding, importance says how much it deserves the
owner's attention, and the two stay apart. No read-state is kept --
the feed is derived on demand, never stored, never a notification.
See ADR-0048.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.insight import InsightKind


@dataclass(frozen=True)
class Discovery:
    """One finding worth showing, with the arithmetic that ranked it."""

    topic: str
    kind: InsightKind
    magnitude: float
    confidence: float
    evidence: tuple[str, ...]
    novelty: float
    importance: float

    def __post_init__(self) -> None:
        if not self.topic:
            raise ValueError("a discovery needs a topic")
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError("importance must lie within [0, 1]")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must lie within [0, 1]")


@dataclass(frozen=True)
class DiscoveryFeed:
    """The findings worth a look, the most discovery-like first."""

    oldest_at: datetime
    latest_at: datetime
    entries: tuple[Discovery, ...]

    def __post_init__(self) -> None:
        if self.oldest_at > self.latest_at:
            raise ValueError("the oldest reading cannot follow the latest")
