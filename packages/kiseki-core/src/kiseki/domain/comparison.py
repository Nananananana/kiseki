"""What changed between two readings, with the arithmetic attached.

A comparison judges nothing the numbers do not show: every entry
carries the strength and the evidence count on both sides, so
"stronger" is a statement about two numbers the reader can see.
Nothing is stored; a comparison is recomputed from the kept profiles
it reads. See ADR-0045.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique

from kiseki.domain.shared.moment import naive


@unique
class ChangeKind(Enum):
    """The changes a comparison knows how to state."""

    APPEARED = "appeared"
    GONE = "gone"
    STRONGER = "stronger"
    WEAKER = "weaker"
    STEADY = "steady"


@dataclass(frozen=True)
class ComparisonEntry:
    """One topic's change, with the numbers behind the judgement."""

    topic: str
    change: ChangeKind
    strength_before: float
    strength_after: float
    evidence_before: int
    evidence_after: int
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.topic:
            raise ValueError("a comparison entry needs a topic")
        if self.strength_before < 0 or self.strength_after < 0:
            raise ValueError("strengths cannot be negative")
        if self.evidence_before < 0 or self.evidence_after < 0:
            raise ValueError("evidence counts cannot be negative")


@dataclass(frozen=True)
class Comparison:
    """Every topic's change between two readings, the loudest first."""

    before_at: datetime
    after_at: datetime
    entries: tuple[ComparisonEntry, ...]

    def __post_init__(self) -> None:
        if naive(self.before_at) > naive(self.after_at):
            raise ValueError("the earlier reading cannot follow the later")
