"""Applies the owner's corrections to a derived reading.

A pure function over a Profile: an excluded topic drops its
interest, an excluded evidence reference drops that evidence, and an
interest left with no evidence drops entirely -- the invariant that
every interest carries evidence survives the filter. Scores and
confidences are not recomputed: the reading is filtered, not
re-derived, so the arithmetic stays honest about what produced it.
Stored bytes are never touched. See ADR-0044.
"""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from dataclasses import replace

from kiseki.domain.interests import Interest, Profile

TOPIC_PREFIX = "topic:"


def apply_corrections(profile: Profile, excluded: AbstractSet[str]) -> Profile:
    """The corrected view of one reading. No exclusions, same object."""
    if not excluded:
        return profile
    kept: list[Interest] = []
    for interest in profile.interests:
        if TOPIC_PREFIX + interest.topic in excluded:
            continue
        evidence = tuple(item for item in interest.evidence if item.reference not in excluded)
        if not evidence:
            continue
        if len(evidence) == len(interest.evidence):
            kept.append(interest)
        else:
            kept.append(replace(interest, evidence=evidence))
    return Profile(generated_at=profile.generated_at, interests=tuple(kept))
