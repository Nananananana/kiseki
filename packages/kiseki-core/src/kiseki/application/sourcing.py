"""Which kinds of witness an answer read.

Every derivation cites evidence in one vocabulary -- `caption:`,
`photo:`, `screen:`, `place:`, `topic:` -- and until now that
vocabulary said what a reference points at without saying what kind of
thing it is. With one source that was the same question. With several
it is not: a reader deciding whether to believe an answer wants to
know whether it came from photographs, from screens, or from both.

The mapping is deterministic and total: a reference either matches a
known prefix or it is a topic, which is what the readings of
photographs become. Nothing here needs a model, and nothing changes if
a source is missing -- an answer built from what exists names what
exists. See ADR-0063.
"""

from __future__ import annotations

from collections.abc import Iterable

from kiseki.domain.evidence.source import EvidenceSource, SourceSet, describe

PREFIXES: dict[str, EvidenceSource] = {
    "caption:": EvidenceSource.STAY_CAPTION,
    "photo:": EvidenceSource.SINGLE_CAPTION,
    "screen:": EvidenceSource.SCREEN,
    "place:": EvidenceSource.JOURNEY,
    "stay:": EvidenceSource.STAY_CAPTION,
    "single:": EvidenceSource.SINGLE_CAPTION,
    "profile:": EvidenceSource.KEPT_READING,
}


def source_of(reference: str) -> EvidenceSource:
    """The kind of witness one reference names."""
    for prefix, source in PREFIXES.items():
        if reference.startswith(prefix):
            return source
    return EvidenceSource.PHOTOGRAPH


def sources_of(references: Iterable[str]) -> SourceSet:
    """Every kind of witness a set of references came from."""
    return frozenset(source_of(reference) for reference in references)


def read_from(references: Iterable[str]) -> str:
    """A line naming what an answer read, or empty when it read nothing.

    Silence rather than "read from nothing": an answer with no evidence
    already says so in its own words, and saying it twice in different
    words is not honesty, it is noise.
    """
    sources = sources_of(references)
    if not sources:
        return ""
    return f"read from {describe(sources)}"
