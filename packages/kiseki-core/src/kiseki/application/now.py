"""One screen, instead of six commands held in the head.

Measured, and this is the whole reason: **forty-six commands.** A
person who wants to know how their year went runs six of them and
remembers the results while running the next. Each of the six is
honest and narrow, which was right while the derivations were being
learned and is now the thing to fix -- the parts exist and nothing
puts them together.

    worth a look   what `today` chose, and why now
    what changed   the loudest movements between two kept readings
    what is thin   the limits that bite, from the library's own counts
    what is wrong  what `doctor` found

## Not a shell script with better spacing

The distinction #361 draws. A screen that ran six commands and pasted
their output would be a worse `refresh`: it would inherit six
vocabularies, six empty states, and no way to say that one region is
empty because there is nothing to say and another because a source
was never read.

So this composes **values**, not text. Every region is a derivation
this library already has, and every empty region says which command
would fill it -- the decision `limits` made about naming absent
sources (ADR-0088) and `ask` made about a question it understood and
cannot answer (ADR-0090), applied a third time rather than invented.

## It never reaches a model

Deliberate, and it is what makes the screen worth opening. Every
region here is derived from what is already stored: `today` reads
suggestions, lifecycles and insights; the trend reads kept profiles;
limits and doctor read counts. A `now` that called a model would be a
screen that mostly fails on a machine where the model is away, which
is the state v0.11 spent a version making legible rather than
frightening (ADR-0073).

The model's work has its own commands, and `cost` says what it would
take before it is started.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from kiseki.application.limits import Limit, LimitsReport
from kiseki.application.today import Today
from kiseki.domain.trends import TopicTrend, TrendDirection, TrendReport

MOVEMENTS = 3
"""How many trends a screen shows. Chosen, like `today`'s three, and
for the same reason: it is what a screen holds. Not a setting -- see
ADR-0092 on why a number about layout is the reader's business."""


@dataclass(frozen=True)
class Region:
    """One part of the screen, and what to do when it is empty."""

    name: str
    empty_because: str
    """What the reader would run to fill it. Empty regions are the
    hard part of a screen assembled from sources that may each be
    absent: *nothing to show* and *you have read no notes* tell a
    reader different things, and only the second is actionable."""

    def __post_init__(self) -> None:
        if not self.empty_because.strip():
            raise ValueError("an empty region that cannot say why is a blank space")


WORTH_A_LOOK = Region("worth a look", "`kiseki build` finds places; `kiseki refresh` adds the rest")
WHAT_CHANGED = Region("what changed", "`kiseki profile --keep` twice, a week apart, makes a trend")
WHAT_IS_THIN = Region("what is thin", "nothing is thin, which is the good case")
WHAT_IS_WRONG = Region("what is wrong", "nothing is wrong, which is the good case")

REGIONS = (WORTH_A_LOOK, WHAT_CHANGED, WHAT_IS_THIN, WHAT_IS_WRONG)


@dataclass(frozen=True)
class Now:
    """The whole screen, as values."""

    at: datetime
    today: tuple[Today, ...] = ()
    changed: tuple[TopicTrend, ...] = ()
    thin: tuple[Limit, ...] = ()
    wrong: tuple[str, ...] = ()
    photographs: int = 0
    outings: int = 0
    unread: dict[str, str] = field(default_factory=dict)
    """Region name to the reason it is empty, for the regions that are."""

    @property
    def quiet(self) -> bool:
        """Nothing to show anywhere. Its own answer, and not a fault."""
        return not (self.today or self.changed or self.thin or self.wrong)


def _loudest(trends: TrendReport | None) -> tuple[TopicTrend, ...]:
    """The movements a reader would notice, steady ones left out.

    Ranked by how far a topic moved from its own baseline rather than
    by its strength: a topic that went from nothing to a little has
    moved further, in the only sense a screen can mean, than one that
    was already strong and stayed so.
    """
    if trends is None:
        return ()
    moved = [trend for trend in trends.trends if trend.direction is not TrendDirection.STEADY]
    moved.sort(key=lambda trend: (-abs(trend.strength - trend.baseline), trend.topic))
    return tuple(moved[:MOVEMENTS])


def what_is_happening(
    at: datetime,
    today: tuple[Today, ...],
    trends: TrendReport | None,
    limits: LimitsReport,
    wrong: tuple[str, ...],
    photographs: int,
    outings: int,
) -> Now:
    """One screen from what is already stored. No model is consulted."""
    changed = _loudest(trends)
    thin = tuple(limits.limits)
    unread: dict[str, str] = {}
    for region, filled in (
        (WORTH_A_LOOK, bool(today)),
        (WHAT_CHANGED, bool(changed)),
        (WHAT_IS_THIN, bool(thin)),
        (WHAT_IS_WRONG, bool(wrong)),
    ):
        if not filled:
            unread[region.name] = region.empty_because
    return Now(
        at=at,
        today=today,
        changed=changed,
        thin=thin,
        wrong=wrong,
        photographs=photographs,
        outings=outings,
        unread=unread,
    )
