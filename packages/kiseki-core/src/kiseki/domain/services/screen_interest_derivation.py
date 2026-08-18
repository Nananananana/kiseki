"""Screen readings become interests, carefully.

Deterministic, like every derivation: no model is consulted. A label
must recur to count, the sensitive and settings categories contribute
nothing, and the merge never overwrites what the captions already
read. See ADR-0031.
"""

from collections.abc import Sequence
from datetime import datetime

from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.screen.reading import SENSITIVE_CATEGORIES, ScreenshotReading
from kiseki.domain.services.generic_labels import is_generic

MIN_SCREEN_LABEL_COUNT = 2
"""A label seen on one screenshot is an accident; on two, a pattern
begins. Calibrate against the real library as it grows."""

NON_EVIDENCE_CATEGORIES = frozenset(SENSITIVE_CATEGORIES | {"settings"})
"""Settings screens are about the device, not the person."""

MAX_SCREEN_EVIDENCE = 5
CONFIDENCE_FULL_COUNT = 8
"""Label count at which confidence saturates."""


def derive_screen_interests(
    readings: Sequence[ScreenshotReading],
    at: datetime,
) -> tuple[Interest, ...]:
    """Interests from the answered, non-sensitive screen readings."""
    eligible = [
        reading
        for reading in readings
        if reading.answered and reading.category not in NON_EVIDENCE_CATEGORIES
    ]
    by_label: dict[str, list[ScreenshotReading]] = {}
    for reading in eligible:
        for label in reading.labels:
            if is_generic(label):
                continue
            by_label.setdefault(label, []).append(reading)

    counted = {
        label: sources
        for label, sources in by_label.items()
        if len(sources) >= MIN_SCREEN_LABEL_COUNT
    }
    if not counted:
        return ()
    peak = max(len(sources) for sources in counted.values())

    interests = []
    for label, sources in sorted(counted.items()):
        ordered = sorted(sources, key=lambda reading: reading.created_at)
        evidence = tuple(
            InterestEvidence(
                kind=EvidenceKind.SCREENSHOT,
                reference=f"screen:{reading.photo_id.value}",
                observed_at=reading.created_at,
            )
            for reading in ordered[:MAX_SCREEN_EVIDENCE]
        )
        interests.append(
            Interest(
                topic=label,
                score=len(sources) / peak,
                confidence=min(1.0, len(sources) / CONFIDENCE_FULL_COUNT),
                evidence=evidence,
                first_seen=ordered[0].created_at,
                last_seen=ordered[-1].created_at,
            )
        )
    return tuple(sorted(interests, key=lambda interest: -interest.score))


def merge_screen_interests(
    profile: Profile,
    screen_interests: Sequence[Interest],
) -> Profile:
    """Append-only: a topic the captions already read keeps its reading."""
    taken = {interest.topic for interest in profile.interests}
    added = tuple(interest for interest in screen_interests if interest.topic not in taken)
    if not added:
        return profile
    return Profile(
        generated_at=profile.generated_at,
        interests=profile.interests + added,
    )
