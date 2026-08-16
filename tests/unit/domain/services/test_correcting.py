"""The corrected view: topics and evidence gone, stored bytes untouched."""

from datetime import UTC, datetime

from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.services.correcting import apply_corrections

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _interest(topic: str, *references: str) -> Interest:
    evidence = tuple(
        InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference=reference, observed_at=WHEN)
        for reference in (references or ("caption:aa",))
    )
    return Interest(
        topic=topic,
        score=0.6,
        confidence=0.5,
        evidence=evidence,
        first_seen=WHEN,
        last_seen=WHEN,
    )


def _profile(*interests: Interest) -> Profile:
    return Profile(generated_at=WHEN, interests=tuple(interests))


def test_a_corrected_topic_disappears():
    corrected = apply_corrections(
        _profile(_interest("data"), _interest("ramen")), frozenset({"topic:data"})
    )
    assert [item.topic for item in corrected.interests] == ["ramen"]


def test_corrected_evidence_is_dropped():
    corrected = apply_corrections(
        _profile(_interest("ramen", "caption:aa", "caption:bb")),
        frozenset({"caption:aa"}),
    )
    assert [item.reference for item in corrected.interests[0].evidence] == ["caption:bb"]


def test_an_interest_with_no_evidence_left_disappears():
    corrected = apply_corrections(
        _profile(_interest("ramen", "caption:aa")), frozenset({"caption:aa"})
    )
    assert corrected.interests == ()


def test_no_exclusions_means_the_same_profile():
    profile = _profile(_interest("ramen"))
    assert apply_corrections(profile, frozenset()) is profile


def test_unrelated_references_change_nothing():
    profile = _profile(_interest("ramen"))
    corrected = apply_corrections(profile, frozenset({"topic:skiing", "caption:zz"}))
    assert corrected.interests == profile.interests
