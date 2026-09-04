"""What the library already knows, offered as facts to an answer.

`ask` retrieves captions and reads them. That is right for *what did I
eat in Seoul*, and it is the wrong instrument for most of what people
actually type. Measured, on a library with an index built:

    "where do I keep going back to?"
      -> "a place with an outdoor bath, as indicated by the steam
          over it [F3]"

    "am I going out less than last year?"
      -> "no evidence found for this question"

**The first is worse than the second.** The library *knows* where the
owner keeps going back to -- `kiseki places` says twelve visits, about
every seven days -- and retrieval answered a question about a pattern
by searching captions for words, which is how a library sounds
confident and says nothing. The second is the same failure being
honest about itself.

Neither is a retrieval problem. Both are a **grounding** problem: the
facts that answer those questions were never offered.

## What this module is

Every derivation this library already ran, turned into short sentences
a model can cite, each carrying where it came from. Places and their
cadence; interests with their confidence; trends; the shape of how
often somebody goes out.

They are facts in exactly the sense retrieval's facts are: derived
from the owner's own data, on the owner's own machine, and traceable
to the derivation that produced them. **Nothing here invents
anything.** A grounding fact that cannot name its source is a bug, and
`__post_init__` refuses one.

## Why this is not "let the model guess"

The rule that makes this library worth trusting is that an answer
cites what it rests on, and says so when nothing supports one. That
rule is kept. What changes is the size of the closed list the model is
allowed to use.

Refusing to answer *where do I keep going back to* on a library that
holds the answer is not caution. It is the answer being in a different
table from the one that was searched.

When there is genuinely nothing, this yields nothing, and `ask` still
says so -- and can now say what it *would* have been able to answer,
which is more useful than silence.

## No coordinates, ever

A grounding fact travels into a prompt, and a prompt is the one place
in this library where a place could reach prose. So a place is
described by its cadence and its shares and never by where it is --
which is what `ADR-0040` already decided for anchors, applied to the
one path that did not exist when it was written.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.interests import Profile
from kiseki.domain.outing.outing import Outing
from kiseki.domain.trends import TrendReport

PLACE = "place"
INTEREST = "interest"
TREND = "trend"
RHYTHM = "rhythm"

KINDS = (PLACE, INTEREST, TREND, RHYTHM)


@dataclass(frozen=True)
class Grounding:
    """One thing the library knows, and where it knows it from."""

    kind: str
    text: str
    """A sentence, already in the owner's terms, that a model may cite."""

    source: str
    """Which derivation produced it -- `kiseki places`, `kiseki profile`
    and so on -- so a reader who doubts a claim can go and look at the
    thing that made it. That is the whole difference between this and
    a model's recollection."""

    observed_at: datetime | None = None
    """When, where the fact has a when. `None` where it is about a
    pattern rather than a moment."""

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"{self.kind!r} is not a kind of grounding")
        if not self.text.strip():
            raise ValueError("a grounding fact with no text says nothing")
        if not self.source.strip():
            raise ValueError("a grounding fact that cannot name its source is a bug")


def _cadence(anchor: Anchor) -> str:
    days = max(1, (anchor.period.end - anchor.period.start).days)
    every = days / anchor.visit_days if anchor.visit_days else days
    return f"about every {every:.0f} days"


def from_anchors(anchors: Sequence[Anchor], limit: int = 5) -> list[Grounding]:
    """Places returned to, without naming or locating them."""
    ordered = sorted(anchors, key=lambda anchor: anchor.visit_days, reverse=True)
    return [
        Grounding(
            kind=PLACE,
            text=(
                f"Place {index}: returned to on {anchor.visit_days} separate days, "
                f"{_cadence(anchor)}, between {anchor.period.start:%Y-%m-%d} and "
                f"{anchor.period.end:%Y-%m-%d}. "
                f"{anchor.night_share:.0%} of those days included a photograph at night, "
                f"{anchor.daytime_share:.0%} during working hours."
            ),
            source="kiseki places",
            observed_at=anchor.period.end,
        )
        for index, anchor in enumerate(ordered[:limit], start=1)
    ]


PLACE_PREFIX = "place:"
"""An interest whose topic is a coordinate.

`exporting.py` refuses these outright, and `narrative.py` filters them
before any prose is written. **This module had to learn the same rule
the hard way**: the first run of grounded `ask` produced

    ...if these locations align with the interests
    'place:35.01160,135.76810' and 'place:34.83500,135.46900'

A profile interest's topic can be a coordinate, and passing topics
through unfiltered put two of them into a prompt, from which the model
printed them. ADR-0047 says a place never leaves; a prompt is a place
it can leave from, and this path did not exist when that was written.

The place facts above carry the same information safely -- cadence and
shares, never a coordinate -- so nothing is lost by dropping these."""


def from_profile(profile: Profile | None, limit: int = 8) -> list[Grounding]:
    """Interests, with the confidence the derivation gave them.

    Place topics are dropped rather than blurred. A blurred coordinate
    in a prompt is still a coordinate, and the model has no reason to
    treat it as one.
    """
    if profile is None:
        return []
    ordered = sorted(
        (one for one in profile.interests if not one.topic.startswith(PLACE_PREFIX)),
        key=lambda one: one.score,
        reverse=True,
    )
    return [
        Grounding(
            kind=INTEREST,
            text=(
                f"'{interest.topic}' is an interest with score {interest.score:.2f} "
                f"and confidence {interest.confidence:.2f}, first seen "
                f"{interest.first_seen:%Y-%m-%d}, last seen {interest.last_seen:%Y-%m-%d}."
            ),
            source="kiseki profile",
            observed_at=interest.last_seen,
        )
        for interest in ordered[:limit]
    ]


def from_trends(trends: TrendReport | None, limit: int = 6) -> list[Grounding]:
    """What grew, shrank or held steady."""
    if trends is None:
        return []
    return [
        Grounding(
            kind=TREND,
            text=(
                f"'{trend.topic}' is {trend.direction.value}: strength "
                f"{trend.strength:.2f} against a baseline of "
                f"{trend.baseline:.2f}."
            ),
            source="kiseki trend",
        )
        for trend in [one for one in trends.trends if not one.topic.startswith(PLACE_PREFIX)][
            :limit
        ]
    ]


def from_outings(outings: Sequence[Outing]) -> list[Grounding]:
    """How often the owner goes out, and over what span.

    One fact rather than one per outing: two hundred outings would
    crowd everything else out of the prompt, and the question this
    answers is about the shape.
    """
    if not outings:
        return []
    ordered = sorted(outings, key=lambda outing: outing.time_range.start)
    first, last = ordered[0].time_range.start, ordered[-1].time_range.end
    days = max(1, (last - first).days)
    stops = sum(outing.stop_count for outing in ordered)
    return [
        Grounding(
            kind=RHYTHM,
            text=(
                f"{len(ordered)} outings between {first:%Y-%m-%d} and {last:%Y-%m-%d}: "
                f"about one every {days / len(ordered):.0f} days, {stops} stops in all, "
                f"averaging {stops / len(ordered):.1f} stops an outing."
            ),
            source="kiseki report",
            observed_at=last,
        )
    ]


def numbered(facts: Sequence[Grounding], start: int = 1) -> str:
    """The closed list a model may use, as [G1], [G2]..."""
    return "\n".join(
        f"[G{index}] ({fact.kind}) {fact.text}" for index, fact in enumerate(facts, start=start)
    )
