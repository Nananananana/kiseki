"""Note readings become interests, carefully.

Deterministic, like every derivation: no model is consulted here. The
model already ran, in a producer, and what arrived is a category and a
handful of labels.

Three guards, and the shape is the one screen readings already use
(ADR-0031):

A label must recur. Written once it is a passing thought; written on
two separate days it is a subject the owner came back to. The
threshold is a guess until there is a year of notes to calibrate
against, and it is written down as one.

The sensitive categories contribute nothing. They carry no labels at
all -- the type refuses them (ADR-0075) -- so this is the second lock
on a door that is already locked, and worth having for the day
somebody adds a category and forgets.

The merge never overwrites what the photographs read. A topic the
captions already found keeps its reading, because a photograph of a
thing is stronger evidence of caring about it than a word in a file.

What a note reaches that a photograph cannot: the profile says
`python` because a screen was photographed, and says nothing about
what the owner was thinking while they typed. See ADR-0080.
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
from kiseki.domain.note.reading import SENSITIVE_CATEGORIES, NoteReading
from kiseki.domain.services.generic_labels import is_generic

MIN_NOTE_DAYS = 2
"""How many separate days a label must appear on before it counts.

Written once, a word is a passing thought. Written again a week later,
it is something the owner came back to -- which is the whole reason a
note reading is keyed by its day (ADR-0076). A guess until there is a
year of notes to calibrate against, exactly as MIN_SCREEN_LABEL_COUNT
is."""

MAX_NOTE_EVIDENCE = 5

CONFIDENCE_FULL_DAYS = 6
"""Days at which confidence saturates. Lower than the screen
equivalent: a person does not write about the same subject eight times
unless they mean it."""


def derive_note_interests(readings: Sequence[NoteReading]) -> tuple[Interest, ...]:
    """Interests from the answered, non-sensitive note readings."""
    eligible = [
        reading
        for reading in readings
        if reading.answered and reading.category not in SENSITIVE_CATEGORIES
    ]
    by_label: dict[str, list[NoteReading]] = {}
    for reading in eligible:
        for label in reading.labels:
            if is_generic(label):
                continue
            by_label.setdefault(label, []).append(reading)

    counted = {
        label: sources
        for label, sources in by_label.items()
        if len({source.day for source in sources}) >= MIN_NOTE_DAYS
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
                kind=EvidenceKind.NOTE,
                reference=f"note:{reading.reference.removeprefix('note:')}",
                observed_at=datetime.combine(reading.day, time()),
            )
            for reading in ordered[:MAX_NOTE_EVIDENCE]
        )
        interests.append(
            Interest(
                topic=label,
                score=days / peak,
                confidence=min(1.0, days / CONFIDENCE_FULL_DAYS),
                evidence=evidence,
                first_seen=datetime.combine(ordered[0].day, time()),
                last_seen=datetime.combine(ordered[-1].day, time()),
            )
        )
    return tuple(sorted(interests, key=lambda interest: -interest.score))


def merge_note_interests(
    profile: Profile,
    note_interests: Sequence[Interest],
) -> Profile:
    """Append-only: a topic the photographs already read keeps its reading."""
    taken = {interest.topic for interest in profile.interests}
    added = tuple(interest for interest in note_interests if interest.topic not in taken)
    if not added:
        return profile
    return Profile(
        generated_at=profile.generated_at,
        interests=profile.interests + added,
    )
