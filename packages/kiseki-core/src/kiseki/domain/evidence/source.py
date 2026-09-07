"""Where a piece of evidence came from, and what may be missing.

Nine versions read one kind of record, so nothing ever had to say
which kind. The next two add more, and every one of them will be
absent for most readers most of the time: a library with photographs
and nothing else must behave exactly as it does today, and a library
with step counts and no screenshots must behave exactly as well.

That is not a courtesy to be remembered. A derivation declares the
sources it can read, works with any subset of them, and names the ones
its answer came from; a test matrix removes each source in turn and
fails the build if anything requires one. The library already does this
for a model that will not answer (ADR-0037 keeps retrieval on the words
channel) and for a gazetteer nobody downloaded (places stay unnamed);
this raises it to a rule, before the sources that need it arrive.

See ADR-0063.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum, unique

VIDEO = "video"
"""Reserved for proposals/0008. Daily activity and the web have both
since stopped being reserved and become members below -- the first
promptly, the second three releases late, which is what the test
beside this file now exists to prevent."""


@unique
class EvidenceSource(Enum):
    """A kind of witness. Any of them may be absent."""

    PHOTOGRAPH = "photograph"
    JOURNEY = "journey"
    STAY_CAPTION = "stay caption"
    SINGLE_CAPTION = "single caption"
    SCREEN = "screen reading"
    KEPT_READING = "kept reading"
    ACTIVITY = "daily activity"
    NOTE = "note"
    PAGE = "page reading"
    """Late, and it should not have been. WebRecord v1 shipped in
    v0.11 and this vocabulary did not grow with it, so every page the
    owner read was reported as a photograph until somebody asked what
    the library would do with a source that was not a camera."""

    @property
    def label(self) -> str:
        return self.value


SourceSet = frozenset[EvidenceSource]

EVERYTHING: SourceSet = frozenset(EvidenceSource)


def describe(sources: Iterable[EvidenceSource]) -> str:
    """The sources an answer read, in a fixed order, for a reader.

    Named in the enum's own order rather than alphabetically, so the
    phrase reads the way the pipeline runs: what was seen, then where,
    then what was said about it.
    """
    present = [source for source in EvidenceSource if source in set(sources)]
    if not present:
        return "nothing"
    labels = [source.label for source in present]
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " and " + labels[-1]
