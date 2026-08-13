"""Shared contract for every ProfileRepository implementation.

Applied to both the fake and the SQLite implementation, in the same
fixture style as the other repository contracts. A fake that drifts
from the real thing is worse than no fake at all.
"""

from datetime import UTC, datetime

import pytest
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.ports.profiles import ProfileRepository


def build_profile(generated_at: datetime, topic: str = "anchor-1") -> Profile:
    evidence = (
        InterestEvidence(
            kind=EvidenceKind.VISIT,
            reference=topic,
            observed_at=generated_at,
        ),
    )
    interest = Interest(
        topic=topic,
        score=0.8,
        confidence=0.6,
        evidence=evidence,
        first_seen=generated_at,
        last_seen=generated_at,
    )
    return Profile(generated_at=generated_at, interests=(interest,))


def _at(day: int) -> datetime:
    return datetime(2026, 3, day, 12, tzinfo=UTC)


class ProfileRepositoryContract:
    @pytest.fixture
    def profiles(self) -> ProfileRepository:
        raise NotImplementedError("override the 'profiles' fixture")

    def test_latest_is_none_before_any_save(self, profiles: ProfileRepository) -> None:
        assert profiles.latest() is None

    def test_history_is_empty_before_any_save(self, profiles: ProfileRepository) -> None:
        assert profiles.history() == ()

    def test_latest_returns_the_saved_profile(self, profiles: ProfileRepository) -> None:
        profile = build_profile(_at(1))
        profiles.save(profile)
        assert profiles.latest() == profile

    def test_latest_returns_the_most_recent_save(self, profiles: ProfileRepository) -> None:
        earlier = build_profile(_at(1))
        later = build_profile(_at(2))
        profiles.save(earlier)
        profiles.save(later)
        assert profiles.latest() == later

    def test_history_keeps_every_save_oldest_first(self, profiles: ProfileRepository) -> None:
        first = build_profile(_at(1))
        second = build_profile(_at(2))
        profiles.save(first)
        profiles.save(second)
        assert profiles.history() == (first, second)

    def test_a_saved_profile_keeps_its_evidence(self, profiles: ProfileRepository) -> None:
        profiles.save(build_profile(_at(1), topic="anchor-7"))
        recalled = profiles.latest()
        assert recalled is not None
        interest = recalled.interests[0]
        assert interest.topic == "anchor-7"
        assert interest.evidence[0].kind is EvidenceKind.VISIT
        assert interest.evidence[0].reference == "anchor-7"
