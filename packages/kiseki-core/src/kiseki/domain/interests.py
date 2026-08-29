"""What the evidence says someone cares about.

An interest is an interpretation, never a measurement. Measures count
and stay silent about meaning; an interest is a reading of those
counts, and a reading can be wrong. The domain therefore refuses to
construct an interest that could not be checked: every interest names
the evidence it rests on and a confidence in the reading itself.
See ADR-0016.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique

from kiseki.domain.shared.moment import naive


@unique
class EvidenceKind(Enum):
    """The kind of observation an interest rests on.

    SCREENSHOT is reserved: no screenshot source exists yet, but the
    kind is named now so stored evidence stays readable when one
    arrives in a later version.
    """

    VISIT = "visit"
    PHOTOGRAPH = "photograph"
    SCREENSHOT = "screenshot"
    NOTE = "note"


@dataclass(frozen=True)
class InterestEvidence:
    """One observation supporting an interest.

    The reference points at the thing observed: an anchor for a visit,
    a photograph identifier for a caption. It is a reference rather
    than a copy, so the profile never duplicates personal data.
    """

    kind: EvidenceKind
    reference: str
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.reference:
            raise ValueError("evidence must reference the thing observed")


@dataclass(frozen=True)
class Interest:
    """A reading of the evidence: a topic someone appears to care about.

    Score and confidence are deliberately separate. Score says how
    strongly the evidence points at the topic; confidence says how far
    the evidence can be trusted to support that reading at all. Twelve
    visits over two years earn a high score with high confidence; two
    visits last week may earn the same score with much less.
    """

    topic: str
    score: float
    confidence: float
    evidence: tuple[InterestEvidence, ...]
    first_seen: datetime
    last_seen: datetime

    def __post_init__(self) -> None:
        if not self.topic:
            raise ValueError("an interest needs a topic")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must lie within [0, 1]")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must lie within [0, 1]")
        if not self.evidence:
            raise ValueError("an interest without evidence is a guess; refuse to build it")
        if naive(self.first_seen) > naive(self.last_seen):
            raise ValueError("first_seen must not follow last_seen")


@dataclass(frozen=True)
class Profile:
    """Every interest read from one build, and when it was read.

    A profile may be empty: a library with too little evidence yields
    no interests, and that emptiness is itself a finding.
    """

    generated_at: datetime
    interests: tuple[Interest, ...]

    def ranked(self) -> tuple[Interest, ...]:
        """Interests from strongest to weakest, ties in given order."""
        return tuple(sorted(self.interests, key=lambda interest: interest.score, reverse=True))
