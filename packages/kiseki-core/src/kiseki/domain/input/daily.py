"""A day's worth of typing and clicking, counted and nothing more.

The sibling of `DailyActivity`, and the same argument: the least
sensitive thing a keyboard knows about a person is how many times it
was pressed today. No key names, no words, no application names, no
window titles, no times of day, no position -- counts per calendar
day, produced by the owner's own recorder.

It is here because a day has more than one face. Photographs say where
somebody went, notes say what they wrote, pages say what they read,
steps say how far they walked; this says how long they were at the
keys. Five faces of one day, and until now the library held four.

What it is not: a measure of productivity, and not evidence of an
interest. Fifteen thousand keystrokes is not a topic and cannot become
one -- this reaches `report`, `privacy` and `limits` as a count, and
the profile never sees it. That is the same place `DailyActivity`
occupies, and it is deliberate: the case for admitting it to an
interest has not been made, and would need a corpus rather than an
argument (ADR-0091, and #350 for the shape of that argument).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

MAX_PLAUSIBLE_EVENTS = 2_000_000
"""Beyond this a number is a fault in the export rather than a day.

Deliberately absurd, as `MAX_PLAUSIBLE_STEPS` is: two million events
is about twenty-three a second for a whole day without pause. The
library refuses the impossible and never argues with the merely
unusual."""

MINUTES_IN_A_DAY = 24 * 60


@dataclass(frozen=True)
class DailyInput:
    """One day at the keys, as the owner's own recorder counted it."""

    day: date
    active_minutes: int
    events: int
    by_family: dict[str, int]
    """Events split by kind of input -- key, button, wheel, motion.
    A shape rather than a vocabulary: the library stores what it is
    given and interprets none of it, so a recorder with a family this
    one has never heard of is not refused."""

    apps: int | None = None
    """How many applications were touched. A count, never a name."""

    corrections: int | None = None
    """Backspaces and undos, where the recorder could count them.

    `None` is not zero, and the difference matters: a recorder reading
    a redacted or structural log knows the events but not which key
    each was, so it cannot count a correction at all. Reporting zero
    there would turn *nobody could count* into *there were none*, and
    a reader has no way back from that. So the field is absent when it
    is unknown, and a producer that cannot count omits it."""

    def __post_init__(self) -> None:
        if self.events < 0:
            raise ValueError("a day cannot have fewer than no events")
        if self.events > MAX_PLAUSIBLE_EVENTS:
            raise ValueError("that is not a day at a keyboard; check the export")
        if not 0 <= self.active_minutes <= MINUTES_IN_A_DAY:
            raise ValueError("a day holds between no minutes and all of them")
        if any(count < 0 for count in self.by_family.values()):
            raise ValueError("a family cannot have fewer than no events")
        if sum(self.by_family.values()) > self.events:
            raise ValueError("the families hold more events than the day did")
        if self.apps is not None and self.apps < 0:
            raise ValueError("a count of applications cannot be negative")
        if self.corrections is not None and self.corrections < 0:
            raise ValueError("a count of corrections cannot be negative")

    @property
    def counted_corrections(self) -> bool:
        """Whether the recorder was able to count corrections at all."""
        return self.corrections is not None
