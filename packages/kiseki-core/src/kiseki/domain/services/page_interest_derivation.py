"""Page readings become interests, more carefully than notes did.

Deterministic, like every derivation. The producer classified an
address and a title into a category and a handful of labels; nothing
here reads a page.

The shape is the note derivation's (ADR-0080), with the thresholds
moved and made the owner's. A page is weaker evidence than a note on
three counts, and none of them is visible in a `PageReading`:

    opening is not choosing     a link was clicked, a tab restored
    the dwell floor is a guess  under ten seconds discarded, the
                                middle is probably attention
    the classification is thin  an address and a title, never the page

A derivation that treated a page like a note would treat a click as
a sentence. So a label must recur on more separate days -- four by
default, against a note's two -- and confidence saturates later.
Both numbers are chosen, not measured; `kiseki settings` says so,
and they are `[derivation]` settings so a corpus can move them.

The unlabelled categories contribute nothing: they carry no labels
by construction (the type refuses them), so this is the second lock
on a door already locked.

The merge is append-only and last. A topic the photographs, screens
or notes already read keeps its reading; a page adds only what
nothing else has seen. Two kinds naming one topic are not two
witnesses here -- nothing across kinds is summed until #390 decides
how kinds weigh. See ADR-0089.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time

from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.services.generic_labels import is_generic
from kiseki.domain.shared.settings import PageSettings
from kiseki.domain.web.reading import UNLABELLED_CATEGORIES, PageReading

MAX_PAGE_EVIDENCE = 5


def derive_page_interests(
    readings: Sequence[PageReading],
    settings: PageSettings | None = None,
) -> tuple[Interest, ...]:
    """Interests from the answered, labelled page readings."""
    rules = settings if settings is not None else PageSettings()
    eligible = [
        reading
        for reading in readings
        if reading.answered and reading.category not in UNLABELLED_CATEGORIES
    ]
    by_label: dict[str, list[PageReading]] = {}
    for reading in eligible:
        for label in reading.labels:
            if is_generic(label):
                continue
            by_label.setdefault(label, []).append(reading)

    counted = {
        label: sources
        for label, sources in by_label.items()
        if len({source.day for source in sources}) >= rules.min_days
    }
    if not counted:
        return ()
    peak = max(len({source.day for source in sources}) for sources in counted.values())

    interests = []
    for label, sources in sorted(counted.items()):
        ordered = sorted(sources, key=lambda reading: reading.day)
        days = len({source.day for source in sources})
        evidence = tuple(
            InterestEvidence(
                kind=EvidenceKind.PAGE,
                reference=f"page:{reading.reference.removeprefix('page:')}",
                observed_at=datetime.combine(reading.day, time()),
            )
            for reading in ordered[:MAX_PAGE_EVIDENCE]
        )
        interests.append(
            Interest(
                topic=label,
                score=days / peak,
                confidence=min(1.0, days / rules.confidence_full_days),
                evidence=evidence,
                first_seen=datetime.combine(ordered[0].day, time()),
                last_seen=datetime.combine(ordered[-1].day, time()),
            )
        )
    return tuple(sorted(interests, key=lambda interest: -interest.score))


def merge_page_interests(
    profile: Profile,
    page_interests: Sequence[Interest],
) -> Profile:
    """Append-only, and last: every other kind keeps its reading."""
    taken = {interest.topic for interest in profile.interests}
    added = tuple(interest for interest in page_interests if interest.topic not in taken)
    if not added:
        return profile
    return Profile(
        generated_at=profile.generated_at,
        interests=profile.interests + added,
    )
