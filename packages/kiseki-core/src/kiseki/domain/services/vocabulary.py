"""How much of a change is the vocabulary rather than the person.

A comparison between two readings assumes they speak the same
language. Early in a library's life they do not: the readings are
still being made, and each one knows words the last did not. The real
library's first nine days went 19, 498, 190, 251, 579, 784, 781, 695,
695 topics -- and a trend across that reports six hundred arrivals,
almost none of which are new interests.

The measure is the share of the two vocabularies that both readings
hold. On those nine days it ran from 0.03 to 1.00, and the two pairs
where the reading had settled were 0.93 and 1.00; every pair from the
days the model was still working sat at 0.73 or below. So 0.8 is
where a comparison stops being about the person and starts being
about the words available to describe them.

Growth alone will not do: one pair shrank to 0.38 times its size and
still shared only a third of its vocabulary. What matters is overlap
in both directions, which is what this counts.

Nothing is suppressed. The comparison is printed as it always was,
and the reader is told what they are looking at. See ADR-0071.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

SETTLED_SHARE = 0.8
"""Above this, two readings speak the same language and a comparison
between them is about the person. Below it, the vocabulary moved."""


@dataclass(frozen=True)
class Overlap:
    """What two readings had, and what they had in common."""

    before: int
    after: int
    shared: int

    def __post_init__(self) -> None:
        if self.shared > min(self.before, self.after):
            raise ValueError("more was shared than either reading held")

    @property
    def union(self) -> int:
        return self.before + self.after - self.shared

    @property
    def share(self) -> float:
        """The fraction of everything named that both readings named."""
        return self.shared / self.union if self.union else 1.0

    @property
    def settled(self) -> bool:
        return self.share >= SETTLED_SHARE

    @property
    def caution(self) -> str:
        """What the reader should know, or nothing worth saying."""
        if self.settled:
            return ""
        return (
            f"  {self.shared} of {self.union} topics appear in both readings;"
            " the rest is the vocabulary changing, not the interests"
        )


def overlap_of(pairs: Iterable[tuple[float, float]]) -> Overlap:
    """Count the overlap from rows that carry a before and an after.

    Derived from the rows the listing shows, so the count can never
    disagree with what is printed above it. A strength of zero means
    the reading did not name the topic at all.
    """
    before = after = shared = 0
    for was, now in pairs:
        in_before = was > 0.0
        in_after = now > 0.0
        before += int(in_before)
        after += int(in_after)
        shared += int(in_before and in_after)
    return Overlap(before=before, after=after, shared=shared)
