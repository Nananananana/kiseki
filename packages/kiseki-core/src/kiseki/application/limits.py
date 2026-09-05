"""What this library cannot tell you, counted from what it holds.

See ADR-0088 for the decision this module turns on.

`kiseki privacy` was this move, made in v0.11 for the same reason
(ADR-0074). It used to *assert* that nothing left the machine; it now
*computes* what leaves from the settings in force. The day it stopped
being a promise and became a report, it was found to have been wrong
for years.

This is that treatment applied to the reach of an answer. The argument
is that **a tool trusted past its reach is worse than no tool**,
because the behaviour it licenses is riskier than the behaviour it
replaced. A reader who knows the library holds nine days of readings
will not ask it about two years; a reader who does not, will.

## No threshold is invented here

This is the whole of the design, and it is a restriction rather than a
feature.

It would be easy to write *your notes are too few* and pick the number
that makes the sentence true. That number would be its author's
opinion wearing a measurement's clothes, and this command exists to
replace exactly that kind of sentence. `SETTLED_SHARE` is the one
threshold in this library that was earned -- nine days of real
readings, overlaps of 0.93 and 1.00 once settled against 0.73 and
below while the model was still working (ADR-0071) -- and no corpus
exists yet to earn another (#309).

So every limit below is one of three things:

    a zero        a source is absent. Nothing to calibrate: none is none
    a span        stated, never judged. The reader knows their question
    an earned     `SETTLED_SHARE`, reused rather than reinvented
    threshold

**A count that is small but not zero is printed and not judged.** Four
notes may be plenty or nothing depending on the question, and this
module does not know the question. That is ADR-0010 -- a measure
counts and never explains -- applied to the one place where the
temptation to explain is strongest.

## What this cannot compute is not here

*An interest that appears in no photograph is invisible, and the
library has no way to know it is missing.* That is true, it is the
sharpest limit of all, and no count on disk implies it. It lives in
`interfaces/claims.py` beside `NEVER_STORED`, where every line already
carries the name of the test that fails if it stops being true.

The split is structural rather than editorial: a limit that can be
counted is computed in this layer, and a limit that can only be
asserted sits in the layer that already has a discipline for
assertions. Neither list can quietly absorb the other.

## Naming sources is a disclosure, and `privacy` already made it

*You have no notes* says something about the owner. It is also
precisely what `kiseki privacy` has printed since v0.11, from the same
counts, so this adds no disclosure that did not already exist -- and
the alternative, a limits report that will not say which source is
missing, cannot do its job.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from kiseki.domain.services.vocabulary import Overlap

PHOTOGRAPHS = "photographs"
NOTES = "notes"
PAGES = "pages"
ACTIVITY = "activity"
SCREENS = "screens"

LOSS: dict[str, str] = {
    PHOTOGRAPHS: "where you went and what was in front of you",
    NOTES: "what you wrote for yourself",
    PAGES: "what you read",
    ACTIVITY: "how your days were spent",
    SCREENS: "what you had open",
}
"""What each source carries, and therefore what its absence costs.

Keyed by name so a source that is added without deciding what its
absence means cannot reach a report: `Source.__post_init__` refuses an
unknown name rather than printing a blank."""


@dataclass(frozen=True)
class Span:
    """The days some evidence covers, end to end."""

    first: date
    last: date

    def __post_init__(self) -> None:
        if self.last < self.first:
            raise ValueError("a span cannot end before it starts")

    @property
    def days(self) -> int:
        """Inclusive, so one day of photographs is a span of 1."""
        return (self.last - self.first).days + 1

    def __str__(self) -> str:
        return f"{self.first:%Y-%m-%d} to {self.last:%Y-%m-%d}"


@dataclass(frozen=True)
class Source:
    """One kind of evidence: how much of it, and over what days."""

    name: str
    count: int
    span: Span | None = None

    def __post_init__(self) -> None:
        if self.name not in LOSS:
            raise ValueError(f"{self.name!r} has no recorded cost of absence")
        if self.count < 0:
            raise ValueError("a source cannot hold fewer than no readings")
        if self.count == 0 and self.span is not None:
            raise ValueError("a source with nothing in it cannot span days")

    @property
    def absent(self) -> bool:
        return self.count == 0


@dataclass(frozen=True)
class Limit:
    """One thing an answer here cannot do, and why."""

    subject: str

    reading: str
    """What was counted. A measure, in the owner's own numbers."""

    because: str
    """What that costs an answer. The only interpretation in the
    module, and it is about the library rather than about the owner."""


@dataclass(frozen=True)
class LimitsReport:
    """What the library holds, and what that puts out of reach."""

    sources: tuple[Source, ...]
    limits: tuple[Limit, ...]
    overlap: Overlap | None = None

    @property
    def span(self) -> Span | None:
        """Every source's days together, or None on an empty library."""
        spans = [source.span for source in self.sources if source.span is not None]
        if not spans:
            return None
        return Span(
            first=min(span.first for span in spans),
            last=max(span.last for span in spans),
        )

    @property
    def empty(self) -> bool:
        """Nothing has been read at all, which is its own answer."""
        return all(source.absent for source in self.sources)


def limits_of(
    sources: Sequence[Source],
    overlap: Overlap | None = None,
    refusals: int = 0,
    label_silent: int = 0,
    withheld: int = 0,
    unlocated: int = 0,
) -> LimitsReport:
    """Every limit that follows from these counts, and no others.

    `refusals` are captions the model declined and `label_silent` are
    readings that came back with nothing. Both are things that exist,
    are stored, and cannot be reached by a word -- a limit a reader
    would otherwise have to infer from two commands.

    `withheld` is separate and is **not a failure**. A reading in a
    sensitive category is recorded so the producer does not read it
    again and deliberately never labelled: what somebody talks about,
    logs into or pays for is not interest evidence. It limits an
    answer exactly as much as an empty reading does, and it limits it
    for the opposite reason, so the two are never added together.

    They were, at first. On the real library all 80 "label-silent"
    readings were sensitive ones -- 32 chat, 31 auth, 17 finance, and
    not one model failure -- so the report described a privacy
    guarantee working correctly as a shortcoming of the library.

    `unlocated` photographs are the same shape as a refused caption:
    stored, with a time and perhaps a caption, and unable to answer
    one kind of question -- here, *where*. Measured on the real
    library: 417 of 4,950, which the photographs row alone would
    have reported as 4,950 places somebody stood (#397).
    """
    found: list[Limit] = []

    for source in sources:
        if source.absent:
            found.append(
                Limit(
                    subject=source.name,
                    reading="none",
                    because=f"nothing here rests on {LOSS[source.name]}",
                )
            )

    if refusals:
        found.append(
            Limit(
                subject="refused captions",
                reading=str(refusals),
                because=(
                    "these stays are stored and have no words, so no question"
                    " phrased in words will reach them"
                ),
            )
        )

    if label_silent:
        found.append(
            Limit(
                subject="label-silent readings",
                reading=str(label_silent),
                because=(
                    "these were read and came back with nothing, so they count toward no interest"
                ),
            )
        )

    if withheld:
        found.append(
            Limit(
                subject="withheld by category",
                reading=str(withheld),
                because=(
                    "deliberately never labelled: what you talk about, log"
                    " into or pay for is not interest evidence. This narrows"
                    " an answer, and it is the library working rather than"
                    " failing"
                ),
            )
        )

    if unlocated:
        found.append(
            Limit(
                subject="photographs without a place",
                reading=str(unlocated),
                because=(
                    "these are stored with a time and carry no coordinate, so no"
                    " question about where reaches them"
                ),
            )
        )

    if overlap is not None and not overlap.settled:
        found.append(
            Limit(
                subject="vocabulary",
                reading=f"{overlap.shared} of {overlap.union} topics in both readings",
                because=(
                    "a comparison between these two readings is about the"
                    " words available, not about you (ADR-0071)"
                ),
            )
        )

    return LimitsReport(
        sources=tuple(sources),
        limits=tuple(found),
        overlap=overlap,
    )
