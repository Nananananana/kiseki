"""Shared contract for every ProfileRepository implementation.

Any implementation, fake or real, inherits these tests unchanged, so
the fake cannot drift from the behaviour the application relies on.
"""

from datetime import datetime, timezone

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
    return datetime(2026, 3, day, 12, tzinfo=timezone.utc)


class ProfileRepositoryContract:
    """Inherit and implement make_repository to join the contract."""

    def make_repository(self) -> ProfileRepository:
        raise NotImplementedError

    def test_latest_is_none_before_any_save(self) -> None:
        repository = self.make_repository()
        assert repository.latest() is None

    def test_history_is_empty_before_any_save(self) -> None:
        repository = self.make_repository()
        assert repository.history() == ()

    def test_latest_returns_the_saved_profile(self) -> None:
        repository = self.make_repository()
        profile = build_profile(_at(1))
        repository.save(profile)
        assert repository.latest() == profile

    def test_latest_returns_the_most_recent_save(self) -> None:
        repository = self.make_repository()
        earlier = build_profile(_at(1))
        later = build_profile(_at(2))
        repository.save(earlier)
        repository.save(later)
        assert repository.latest() == later

    def test_history_keeps_every_save_oldest_first(self) -> None:
        repository = self.make_repository()
        first = build_profile(_at(1))
        second = build_profile(_at(2))
        repository.save(first)
        repository.save(second)
        assert repository.history() == (first, second)

    def test_a_saved_profile_keeps_its_evidence(self) -> None:
        repository = self.make_repository()
        repository.save(build_profile(_at(1), topic="anchor-7"))
        recalled = repository.latest()
        assert recalled is not None
        interest = recalled.interests[0]
        assert interest.topic == "anchor-7"
        assert interest.evidence[0].kind is EvidenceKind.VISIT
        assert interest.evidence[0].reference == "anchor-7"
