"""Reads the subject readings as interests.

One label becomes one interest, with PHOTOGRAPH evidence pointing at
the captions the label was read from. Labels about the record rather
than the world are left out entirely (ADR-0053). When themes are
given, a theme speaks for its members: the theme aggregates their
sightings, and a label that shares the theme's own name is one of
them rather than a second interest with the same word (a
shared stay counts once) and the absorbed members stop speaking solo.
See ADR-0021 and ADR-0024.

Single-photo captions join the same pool: each contributes one
sighting, dated by its photograph and referenced as photo evidence,
and consent is re-checked at read time. See ADR-0034.

Ambient labels are excluded by share -- everywhere. They neither
become solo interests nor contribute through a theme; a theme left
with fewer than two contributing members is not emitted, and its
remaining member speaks for itself again. Everything here is
deterministic.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.caption.themes import Theme
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence
from kiseki.domain.photo.observation import PhotoObservation
from kiseki.domain.services.generic_labels import is_generic

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

MIN_CONTRIBUTING_MEMBERS = 2
"""A theme needs at least this many non-ambient members with
sightings to be emitted; otherwise its members speak for themselves."""


def derive_subject_interests(
    readings: Sequence[SubjectExtraction],
    captions: Sequence[Caption],
    photos: Sequence[PhotoObservation],
    themes: Sequence[Theme] = (),
    singles: Sequence[SingleCaption] = (),
) -> tuple[Interest, ...]:
    """Read themes and non-ambient labels as interests, strongest first.

    A stay reading contributes one sighting per label, dated by the
    earliest photograph of its caption; a single reading contributes
    one, dated by its photograph. Readings that were refused, whose
    caption is unknown, whose photographs carry no time, or whose
    photograph withheld consent (ADR-0032) are left out entirely.
    """
    captured = {photo.photo_id: photo.captured_at for photo in photos}
    withheld = {photo.photo_id for photo in photos if not photo.may_inform_preferences}
    by_key = {caption.key.value: caption for caption in captions}
    single_by_key = {
        CaptionKey.of([single.photo_id]).value: single for single in singles if single.answered
    }

    sightings: dict[str, list[tuple[datetime, str, str]]] = {}
    counted = 0
    for reading in readings:
        if not reading.answered:
            continue
        caption = by_key.get(reading.key.value)
        if caption is not None:
            times = [captured[pid] for pid in caption.photo_ids if pid in captured]
            if not times:
                continue
            observed = min(times)
            reference = f"caption:{reading.key.value}"
        else:
            single = single_by_key.get(reading.key.value)
            if single is None:
                continue
            if single.photo_id in withheld or single.photo_id not in captured:
                continue
            observed = captured[single.photo_id]
            reference = f"photo:{single.photo_id.value}"
        counted += 1
        for label in {_normalised(raw) for raw in reading.labels}:
            if label and not is_generic(label):
                sightings.setdefault(label, []).append((observed, reading.key.value, reference))

    if not counted:
        return ()

    ambient = {label for label, entries in sightings.items() if _ambient(len(entries), counted)}

    absorbed: set[str] = set()
    theme_entries: dict[str, list[tuple[datetime, str, str]]] = {}
    for theme in themes:
        if is_generic(theme.name):
            continue
        contributing = [
            member for member in theme.members if member in sightings and member not in ambient
        ]
        if len(contributing) < MIN_CONTRIBUTING_MEMBERS:
            continue
        merged: dict[str, tuple[datetime, str]] = {}
        twin = theme.name if theme.name in sightings else None
        if twin is not None:
            for observed, stay, reference in sightings[twin]:
                merged[stay] = (observed, reference)
        for member in contributing:
            for observed, stay, reference in sightings[member]:
                if stay not in merged or observed < merged[stay][0]:
                    merged[stay] = (observed, reference)
        theme_entries[theme.name] = [
            (observed, stay, reference) for stay, (observed, reference) in merged.items()
        ]
        absorbed.update(contributing)
        if twin is not None:
            absorbed.add(twin)

    interests = [_interest_for(name, entries) for name, entries in theme_entries.items()]
    interests += [
        _interest_for(label, entries)
        for label, entries in sightings.items()
        if label not in ambient and label not in absorbed
    ]
    return tuple(sorted(interests, key=lambda interest: (-interest.score, interest.topic)))


def _ambient(occurrences: int, counted: int) -> bool:
    if counted < AMBIENT_MIN_READINGS:
        return False
    return occurrences / counted > AMBIENT_SHARE


def _interest_for(label: str, entries: list[tuple[datetime, str, str]]) -> Interest:
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
            reference=reference,
            observed_at=observed,
        )
        for observed, _stay, reference in _spread(ordered)
    )
    return Interest(
        topic=label,
        score=score,
        confidence=confidence,
        evidence=evidence,
        first_seen=first_seen,
        last_seen=last_seen,
    )


def _spread(ordered: list[tuple[datetime, str, str]]) -> list[tuple[datetime, str, str]]:
    if len(ordered) <= MAX_EVIDENCE:
        return ordered
    return [ordered[0], *ordered[-(MAX_EVIDENCE - 1) :]]


def _normalised(raw: str) -> str:
    return raw.replace("_", " ").strip()
