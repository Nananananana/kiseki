"""What a page was about -- never its address, never its title.

A note is something the owner wrote; a page is something they opened.
That is a weaker signal and a stronger disclosure: weaker because
opening is not choosing, stronger because a browser holds every page
somebody did not mean to keep.

So the type has no field for the address, and none for the title
either. The producer is given both, decides a category and a handful
of labels, and discards the rest before the core sees anything
(ADR-0085). A core that received an address and then dropped it could
not prove it had dropped it.

What survives is a reference -- a **salted** hash of the address, made
by the producer -- so the core can tell that two readings came from
the same page and cannot tell which page, and neither can anybody who
takes the file. A path is a private string and a URL is a public one,
which is why this reference is salted where a note's is not
(ADR-0084).

See `docs/web-record.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

CATEGORIES = (
    "reading",
    "study",
    "work",
    "project",
    "reference",
    "recipe",
    "travel",
    "video",
    "health",
    "money",
    "people",
    "credential",
    "shopping",
    "news",
    "private",
    "other",
)

UNLABELLED_CATEGORIES = frozenset(
    {"health", "money", "people", "credential", "shopping", "news", "private"}
)
"""Recorded and never labelled.

The first four are NoteRecord's sensitive list and are sharper here: a
note about an illness is one somebody sat down to write, and a symptom
typed into a search box at two in the morning is not deliberate at
all. `shopping` because a product page is a purchase in another
costume, and purchases are declined as a source outright. `news`
because labels on news reading would be an inference about politics
and religion from what somebody read once, and no test separates
follows-seismology from reads-one-party's-paper. `private` is the
catch-all, so that what cannot be placed does not land in `other` and
get labels."""

MAX_LABELS = 8


@dataclass(frozen=True)
class PageReading:
    """One reading of one page on one day, or its refusal.

    Not the state of a page. A page returned to across six months is
    six readings, and the returning is the evidence. Forty visits in
    one afternoon are one reading, because opening a tab again is not
    a second interest (ADR-0076).
    """

    reference: str
    day: date
    category: str
    labels: tuple[str, ...]
    model: str
    created_at: datetime
    refused: str | None = None
    prompt_version: str | None = None

    def __post_init__(self) -> None:
        if not self.reference.strip():
            raise ValueError("a page reading needs a reference to the page")
        if self.refused is None and self.category not in CATEGORIES:
            raise ValueError(f"{self.category!r} is not a page category")
        if self.category in UNLABELLED_CATEGORIES and self.labels:
            raise ValueError("a category that carries no labels never carries labels")
        if any(not label.strip() for label in self.labels):
            raise ValueError("a label cannot be blank")
        if len(self.labels) > MAX_LABELS:
            raise ValueError(f"a page carries at most {MAX_LABELS} labels")

    @property
    def answered(self) -> bool:
        return self.refused is None
