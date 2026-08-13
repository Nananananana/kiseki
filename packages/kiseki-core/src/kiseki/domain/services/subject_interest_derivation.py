"""Reads the subject readings as interests.

One label becomes one interest, with PHOTOGRAPH evidence pointing at
the captions the label was read from. This is where interests gain
human-readable topics, as ADR-0017 promised: the label describes what
was photographed, not what a place is for.

Ambient labels are excluded by share: something that appears in more
than a quarter of the readings describes the world the photographs
were taken in, not a choice. The exclusion waits for enough readings
to tell the difference. Everything here is deterministic; see
ADR-0021.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from kiseki.domain.caption.caption import Caption
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence
from kiseki.domain.photo.observation import PhotoObservation

AMBIENT_SHARE = 0.25
"""A label in more than this share of the readings is ambient, not an
interest. Buildings and people are in most photographs of a life;
their presence says nothing about what the person went to see."""

AMBIENT_MIN_READINGS = 8
"""Below this many readings, the share test cannot tell ambient from
interesting -- with one reading, everything is in all of them -- so
nothing is excluded."""

SUBJECT_SCORE_HALF_STAYS = 2
"""Stays at which the score reaches one half. A single sighting is
real evidence (FR-507) but scores modestly; repetition saturates."""

SUBJECT_CONFIDENCE_HALF_STAYS = 4
CONFIDENCE_HALF_SPAN_DAYS = 30
"""The confidence factors, in the shape of ADR-0017: enough stays,
spread over enough time. A subject seen only on one day earns a score
and zero confidence -- signal, but no trust in it being durable yet."""

MAX_EVIDENCE = 10
"""An interest carries the earliest sighting and the most recent ones,
capped. The full record always remains in the caption and subject
stores; the evidence here is for showing, not for storage."""


def derive_subject_interests(
    readings: Sequence[SubjectExtraction],
    captions: Sequence[Caption],
    photos: Sequence[PhotoObservation],
) -> tuple[Interest, ...]:
    """Read every non-ambient label as an interest, strongest first.

    A reading contributes one sighting per label, dated by the
    earliest photograph of its caption. Readings that were refused,
    whose caption is unknown, or whose photographs carry no time are
    left out entirely.
    """
    captured = {photo.photo_id: photo.captured_at for photo in photos}
    by_key = {caption.key.value: caption for caption in captions}

    sightings: dict[str, list[tuple[datetime, str]]] = {}
    counted = 0
    for reading in readings:
        if not reading.answered:
            continue
        caption = by_key.get(reading.key.value)
        if caption is None:
            continue
        times = [captured[pid] for pid in caption.photo_ids if pid in captured]
        if not times:
            continue
        observed = min(times)
        counted += 1
        for label in {_normalised(raw) for raw in reading.labels}:
            if label:
                sightings.setdefault(label, []).append((observed, reading.key.value))

    if not counted:
        return ()

    interests = [
        _interest_for(label, entries)
        for label, entries in sightings.items()
        if not _ambient(len(entries), counted)
    ]
    return tuple(sorted(interests, key=lambda interest: (-interest.score, interest.topic)))


def _ambient(occurrences: int, counted: int) -> bool:
    if counted < AMBIENT_MIN_READINGS:
        return False
    return occurrences / counted > AMBIENT_SHARE


def _interest_for(label: str, entries: list[tuple[datetime, str]]) -> Interest:
    ordered = sorted(entries)
    stays = len(ordered)
    first_seen = ordered[0][0]
    last_seen = ordered[-1][0]
    span_days = (last_seen - first_seen).days

    score = stays / (stays + SUBJECT_SCORE_HALF_STAYS)
    confidence = (stays / (stays + SUBJECT_CONFIDENCE_HALF_STAYS)) * (
        span_days / (span_days + CONFIDENCE_HALF_SPAN_DAYS)
    )

    evidence = tuple(
        InterestEvidence(
            kind=EvidenceKind.PHOTOGRAPH,
            reference=f"caption:{key}",
            observed_at=observed,
        )
        for observed, key in _spread(ordered)
    )
    return Interest(
        topic=label,
        score=score,
        confidence=confidence,
        evidence=evidence,
        first_seen=first_seen,
        last_seen=last_seen,
    )


def _spread(ordered: list[tuple[datetime, str]]) -> list[tuple[datetime, str]]:
    if len(ordered) <= MAX_EVIDENCE:
        return ordered
    return [ordered[0], *ordered[-(MAX_EVIDENCE - 1) :]]


def _normalised(raw: str) -> str:
    return raw.replace("_", " ").strip()
