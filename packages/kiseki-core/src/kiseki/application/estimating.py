"""How long the model work left to do will take, on this machine.

The derivations are not the cost. Measured on this machine, building
stops, outings and anchors for a hundred thousand photographs takes
**1.94 seconds**; captioning the stays it finds takes **eight and a
half hours**. The two ends of this library are four orders of
magnitude apart, and only one of them is worth a reader's attention
before they commit an afternoon.

The work is resumable and always was -- a second run costs nothing for
what is already done. That was never the problem. The problem is that
a reader with fifty thousand photographs types `kiseki refresh`,
watches it caption for twenty minutes, and cannot tell whether they
are near the end or at five percent.

## The rate is measured here, not shipped

A number from the machine this was written on would be a number about
that machine. A 4090 and a laptop with no GPU are different by more
than a factor, and an estimate carrying somebody else's hardware is
worse than no estimate: it is wrong with authority.

So the caller measures, and passes what it measured. This module does
the arithmetic and, more importantly, **refuses to add up stages it
could not count**.

## An estimate that omits a stage is worse than none

Four stages call a model. If one cannot be counted and is quietly left
out, the total is confidently low, the reader plans an hour, and the
work takes three. So a stage this cannot count is carried as
`UNKNOWN`, the total says how many stages it covers, and a reader is
told the estimate is a floor rather than being told a number that
happens to be small.
"""

from collections.abc import Sequence
from dataclasses import dataclass

UNKNOWN = -1
"""A stage whose outstanding work could not be counted. Not zero:
zero means there is nothing to do, and the difference between *nothing
left* and *not known* is the whole reason this constant exists."""


@dataclass(frozen=True)
class Stage:
    """One pass over the library that calls a model."""

    name: str
    outstanding: int
    seconds_each: float | None
    """`None` when nothing measured this stage's rate."""

    what: str
    """What one item is, for a reader who has never run this."""

    @property
    def counted(self) -> bool:
        return self.outstanding != UNKNOWN

    @property
    def estimable(self) -> bool:
        return self.counted and self.seconds_each is not None

    @property
    def seconds(self) -> float:
        if not self.estimable:
            return 0.0
        assert self.seconds_each is not None
        return self.outstanding * self.seconds_each


@dataclass(frozen=True)
class Estimate:
    """What the remaining model work will take, and how sure that is."""

    stages: tuple[Stage, ...]

    @property
    def seconds(self) -> float:
        return sum(stage.seconds for stage in self.stages)

    @property
    def estimable(self) -> tuple[Stage, ...]:
        return tuple(stage for stage in self.stages if stage.estimable)

    @property
    def unestimable(self) -> tuple[Stage, ...]:
        """Stages the total does not include. Named, not dropped."""
        return tuple(stage for stage in self.stages if not stage.estimable)

    @property
    def is_a_floor(self) -> bool:
        """Whether the total is less than the whole answer.

        True the moment any stage is missing, because a reader told
        *about an hour* who then waits three has been misled by
        arithmetic that was correct about the part it did."""
        return bool(self.unestimable)

    @property
    def nothing_to_do(self) -> bool:
        return all(stage.outstanding == 0 for stage in self.stages if stage.counted)


def estimate(stages: Sequence[Stage]) -> Estimate:
    return Estimate(tuple(stages))


def in_words(seconds: float) -> str:
    """A duration a person can act on.

    Deliberately coarse. An estimate from one timed call is not
    accurate to the minute, and printing `4h 17m 33s` would claim a
    precision the measurement does not have.
    """
    if seconds < 60:
        return "under a minute"
    if seconds < 3600:
        return f"about {round(seconds / 60)} minutes"
    hours = seconds / 3600
    if hours < 10:
        return f"about {hours:.1f} hours"
    return f"about {round(hours)} hours"
