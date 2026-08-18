"""Where something outside the library may speak, and how far.

A provider knows things KISEKI cannot: whether it will rain on
Saturday, whether the museum opens at ten. It does not know the owner,
and it must never be able to act as though it did. So the boundary is
shaped to forbid the dangerous thing rather than to discourage it: an
annotator receives suggestions and returns notes about them, and there
is no return path by which it could invent one.

A note is added beside a suggestion, never into it. The suggestion
keeps saying exactly what the owner's own evidence earned, which is
the same posture corrections (ADR-0044), the label stoplist (ADR-0053)
and the answer check (ADR-0054) already take: keep what was said,
judge or annotate at reading time.

No adapter ships with this port. The boundary exists first, tested
against a fake, so that the day a real provider arrives it has a shape
to fit rather than a shape to negotiate. See ADR-0056.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from kiseki.domain.services.suggesting import Suggestion

MAX_NOTE_LENGTH = 120
"""A note annotates; it does not narrate."""


@dataclass(frozen=True)
class ProviderNote:
    """One outside remark about one suggestion."""

    reference: str
    source: str
    note: str

    def __post_init__(self) -> None:
        if not self.reference.strip():
            raise ValueError("a note needs the suggestion it is about")
        if not self.source.strip():
            raise ValueError("a note needs to say who said it")
        if not self.note.strip():
            raise ValueError("an empty note is not a note")
        if len(self.note) > MAX_NOTE_LENGTH:
            raise ValueError("a note annotates; it does not narrate")


class SuggestionAnnotator(Protocol):
    """Adds notes to suggestions. Cannot create, reorder or remove them.

    The signature is the guarantee: suggestions go in, notes come out,
    and a note that names no suggestion the owner was offered is
    discarded by the caller rather than trusted.
    """

    def annotate(self, suggestions: Sequence[Suggestion]) -> Sequence[ProviderNote]: ...

    @property
    def source(self) -> str:
        """Who this is, for the owner to see beside every note."""
        ...
