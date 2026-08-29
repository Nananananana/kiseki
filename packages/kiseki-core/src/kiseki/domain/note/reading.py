"""What a note was about -- never what it said.

A note is the most eloquent thing this library will read and the most
dangerous. A photograph is something the owner pointed a camera at; a
page in a browser history is something they happened to open; a note
is something they wrote, and a folder of them holds a diary, another
person's confidence, a password, a resignation letter.

So the type has no field for the text, the same way a screen reading
has none (ADR-0030). The producer reads the note, decides a category
and a handful of labels, and discards everything else before the core
sees anything. A core that read the text and then dropped it could not
prove it had dropped it; a core that never receives it has nothing to
prove.

The file name goes too. `2026-resignation.md` says as much as its
contents. What survives is a reference -- a hash of the path, made by
the producer -- so the core can tell that two readings came from the
same note and cannot tell which note. The owner asks the producer,
which is where that mapping lives, exactly as a photograph's content
hash lives here and its reduced copy lives there.

See ADR-0075.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

CATEGORIES = (
    "note",
    "reading",
    "study",
    "work",
    "project",
    "recipe",
    "travel",
    "journal",
    "health",
    "money",
    "people",
    "credential",
    "other",
)

SENSITIVE_CATEGORIES = frozenset({"journal", "health", "money", "people", "credential"})
"""Recorded so the producer does not read them again, and never
labelled. A diary, a symptom, a balance, what somebody else told you
in confidence, and anything that looks like a secret: the category is
enough to count, and the labels would be the leak.

`people` is here because a note about a person is mostly about the
person, and they did not choose to be in this library."""

MAX_LABELS = 8
"""A note is not a document to be summarised. Eight labels is a
handful of subjects; more would be the text arriving in pieces."""


@dataclass(frozen=True)
class NoteReading:
    """One model's reading of one note, or its refusal."""

    reference: str
    day: date
    category: str
    labels: tuple[str, ...]
    model: str
    created_at: datetime
    refused: str | None = None
    prompt_version: str | None = None
    """Which prompt version made this reading, when it was recorded.
    None means it was not recorded -- the reading predates the field.
    See ADR-0051."""

    def __post_init__(self) -> None:
        if not self.reference.strip():
            raise ValueError("a note reading needs a reference to the note")
        if self.refused is None and self.category not in CATEGORIES:
            raise ValueError(f"{self.category!r} is not a note category")
        if self.category in SENSITIVE_CATEGORIES and self.labels:
            raise ValueError("a sensitive category never carries labels")
        if any(not label.strip() for label in self.labels):
            raise ValueError("a label cannot be blank")
        if len(self.labels) > MAX_LABELS:
            raise ValueError(f"a note carries at most {MAX_LABELS} labels")

    @property
    def answered(self) -> bool:
        return self.refused is None
