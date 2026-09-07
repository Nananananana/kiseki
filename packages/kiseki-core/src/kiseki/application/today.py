"""One to three things for today, each saying why today.

The hero slot of a reader that is opened every morning, and the reason
to open it: not *here is everything the library knows*, which is a
menu, but *here is what is worth knowing now*, which is an answer.

## Why this is not `suggest` with a limit

`suggest` ranks by how overdue a place is and never asks whether
anything happened lately. A profile that turned dormant this week is
the most interesting thing in the library that day, and `suggest` has
no idea it exists. So this reads three derivations and puts them in
one order:

    overdue      a place past its own cadence -- the longest first
    turned       a topic that stopped being dormant since last week
    lately       an insight whose evidence is within the last week

Nothing here derives anything. Every item is something a command
already says, chosen and given a reason; a reader who disagrees can
run that command and see the whole of it, which is why each item
carries the one it came from.

## The numbers are chosen

`AT_MOST` and `RECENT_DAYS` are guesses, and say so. Three is what a
card holds; a week is what "lately" means to a person opening a
reader each morning. There is no corpus of *what a person wanted to
be shown today* to measure against, and inventing one would be this
module's own rules restated as evidence (the same argument ADR-0090
made about routing).

They are not settings. A threshold the owner can move is one the
library has to defend at every value; these two decide how many cards
a screen holds, which is the reader's business rather than the
library's, and a reader that wants two takes the first two.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from kiseki.domain.insight import Insight, InsightReport
from kiseki.domain.lifecycle import LifecycleReport, LifecycleStage, TopicLifecycle
from kiseki.domain.services.suggesting import Suggestion, SuggestionKind
from kiseki.domain.shared.moment import naive

AT_MOST = 3
"""How many things a morning holds. Chosen, not measured: it is what a
card holds, and a reader wanting fewer takes the first few."""

RECENT_DAYS = 7
"""What "lately" means. Chosen, not measured."""

OVERDUE = "overdue"
TURNED = "turned"
LATELY = "lately"


@dataclass(frozen=True)
class Today:
    """One thing worth knowing now, and why now."""

    kind: str
    topic: str
    why_today: str
    """A sentence a reader can put on a card without rewriting it."""

    source: str
    """The command that says the whole of it, for a reader who
    disagrees with the choosing."""

    def __post_init__(self) -> None:
        if self.kind not in (OVERDUE, TURNED, LATELY):
            raise ValueError(f"{self.kind!r} is not a reason for today")
        if not self.why_today.strip():
            raise ValueError("an item with no reason is a menu entry, not an answer")


def _overdue(suggestions: Sequence[Suggestion]) -> list[Today]:
    found = []
    for item in suggestions:
        if item.kind is not SuggestionKind.REVISIT:
            continue
        if item.days_since is None or item.cadence_days is None:
            continue
        found.append(
            Today(
                kind=OVERDUE,
                topic=item.reference,
                why_today=(
                    f"{item.days_since} days since you were last there, "
                    f"and you used to go about every {item.cadence_days}"
                ),
                source="kiseki suggest",
            )
        )
    return found


def _turned(lifecycle: LifecycleReport | None) -> list[Today]:
    """Topics that stopped being dormant.

    `RETURNED` is the stage that means exactly this, and it is the one
    thing in the library that is *news*: a subject the owner had put
    down and picked up again.
    """
    if lifecycle is None:
        return []
    turned: list[TopicLifecycle] = [
        item for item in lifecycle.lifecycles if item.stage is LifecycleStage.RETURNED
    ]
    return [
        Today(
            kind=TURNED,
            topic=item.topic,
            why_today=(
                f"'{item.topic}' came back after being dormant, "
                f"seen in {item.seen_profiles} readings"
            ),
            source="kiseki lifecycle",
        )
        for item in turned
    ]


def _lately(insights: InsightReport | None, now: datetime) -> list[Today]:
    if insights is None:
        return []
    edge = naive(now) - timedelta(days=RECENT_DAYS)
    fresh: list[Insight] = [
        item
        for item in insights.insights
        if item.last_seen is not None and naive(item.last_seen) >= edge
    ]
    fresh.sort(key=lambda item: (-item.confidence, item.topic))
    return [
        Today(
            kind=LATELY,
            topic=item.topic,
            why_today=(
                f"'{item.topic}' is {item.direction.value} in the last "
                f"{RECENT_DAYS} days, on {len(item.evidence)} sightings"
            ),
            source="kiseki insights",
        )
        for item in fresh
    ]


def what_matters_today(
    suggestions: Sequence[Suggestion],
    lifecycle: LifecycleReport | None,
    insights: InsightReport | None,
    now: datetime,
) -> tuple[Today, ...]:
    """At most three things, in the order a morning wants them.

    Overdue first, because a place you have not been to in six hundred
    days is the loudest thing the library can say. Then what turned,
    then what has been happening. Nothing is invented and nothing is
    ranked against anything from another kind -- the order between
    kinds is fixed and stated rather than computed from scores that
    were never comparable (ADR-0064's argument, applied to ranking).
    """
    ordered = _overdue(suggestions) + _turned(lifecycle) + _lately(insights, now)
    seen: set[str] = set()
    kept: list[Today] = []
    for item in ordered:
        if item.topic in seen:
            continue
        seen.add(item.topic)
        kept.append(item)
        if len(kept) == AT_MOST:
            break
    return tuple(kept)
