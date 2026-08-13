"""The interest values and the promises they refuse to break.

An interest is an interpretation. The domain refuses to construct one
that could not be checked: no evidence, no interest. See ADR-0016.
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any

import pytest
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)


def _when(hour: int = 12) -> datetime:
    return datetime(2026, 3, 1, hour, tzinfo=UTC)


def _evidence(reference: str = "anchor-1") -> InterestEvidence:
    return InterestEvidence(
        kind=EvidenceKind.VISIT,
        reference=reference,
        observed_at=_when(),
    )


def _interest(**overrides: Any) -> Interest:
    values: dict[str, Any] = {
        "topic": "anchor-1",
        "score": 0.8,
        "confidence": 0.6,
        "evidence": (_evidence(),),
        "first_seen": _when(9),
        "last_seen": _when(18),
    }
    values.update(overrides)
    return Interest(**values)


class TestEvidenceKind:
    def test_names_the_three_sources(self) -> None:
        assert EvidenceKind.VISIT.value == "visit"
        assert EvidenceKind.PHOTOGRAPH.value == "photograph"
        assert EvidenceKind.SCREENSHOT.value == "screenshot"

    def test_screenshot_is_named_before_any_source_exists(self) -> None:
        # Reserved: stored evidence must stay readable when a
        # screenshot source arrives in a later version.
        assert EvidenceKind("screenshot") is EvidenceKind.SCREENSHOT


class TestInterestEvidence:
    def test_holds_what_was_observed(self) -> None:
        evidence = _evidence()
        assert evidence.kind is EvidenceKind.VISIT
        assert evidence.reference == "anchor-1"
        assert evidence.observed_at == _when()

    def test_refuses_an_empty_reference(self) -> None:
        with pytest.raises(ValueError):
            _evidence(reference="")

    def test_is_immutable(self) -> None:
        evidence = _evidence()
        with pytest.raises(FrozenInstanceError):
            evidence.reference = "anchor-2"  # type: ignore[misc]


class TestInterest:
    def test_carries_score_confidence_and_evidence(self) -> None:
        interest = _interest()
        assert interest.topic == "anchor-1"
        assert interest.score == 0.8
        assert interest.confidence == 0.6
        assert len(interest.evidence) == 1
        assert interest.first_seen <= interest.last_seen

    def test_refuses_an_empty_topic(self) -> None:
        with pytest.raises(ValueError):
            _interest(topic="")

    def test_refuses_a_score_above_one(self) -> None:
        with pytest.raises(ValueError):
            _interest(score=1.1)

    def test_refuses_a_score_below_zero(self) -> None:
        with pytest.raises(ValueError):
            _interest(score=-0.1)

    def test_accepts_the_score_boundaries(self) -> None:
        assert _interest(score=0.0).score == 0.0
        assert _interest(score=1.0).score == 1.0

    def test_refuses_a_confidence_outside_the_unit_interval(self) -> None:
        with pytest.raises(ValueError):
            _interest(confidence=1.1)
        with pytest.raises(ValueError):
            _interest(confidence=-0.1)

    def test_refuses_an_interest_without_evidence(self) -> None:
        # An interest with no evidence is a guess, and a guess about a
        # person must not be constructible.
        with pytest.raises(ValueError):
            _interest(evidence=())

    def test_refuses_first_seen_after_last_seen(self) -> None:
        with pytest.raises(ValueError):
            _interest(first_seen=_when(18), last_seen=_when(9))

    def test_is_immutable(self) -> None:
        interest = _interest()
        with pytest.raises(FrozenInstanceError):
            interest.score = 0.9  # type: ignore[misc]


class TestProfile:
    def test_holds_interests_and_when_they_were_read(self) -> None:
        profile = Profile(generated_at=_when(), interests=(_interest(),))
        assert profile.generated_at == _when()
        assert len(profile.interests) == 1

    def test_may_be_empty(self) -> None:
        # A library with too little evidence yields no interests, and
        # that emptiness is itself a finding worth keeping.
        profile = Profile(generated_at=_when(), interests=())
        assert profile.interests == ()
        assert profile.ranked() == ()

    def test_ranked_orders_strongest_first(self) -> None:
        weak = _interest(topic="anchor-2", score=0.2)
        strong = _interest(topic="anchor-3", score=0.9)
        middle = _interest(topic="anchor-4", score=0.5)
        profile = Profile(generated_at=_when(), interests=(weak, strong, middle))
        assert [i.topic for i in profile.ranked()] == [
            "anchor-3",
            "anchor-4",
            "anchor-2",
        ]

    def test_ranked_keeps_ties_in_given_order(self) -> None:
        first = _interest(topic="anchor-2", score=0.5)
        second = _interest(topic="anchor-3", score=0.5)
        profile = Profile(generated_at=_when(), interests=(first, second))
        assert [i.topic for i in profile.ranked()] == ["anchor-2", "anchor-3"]
