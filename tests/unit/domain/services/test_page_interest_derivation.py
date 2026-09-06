"""A page becomes an interest, more carefully than a note (ADR-0089)."""

from datetime import UTC, date, datetime

import pytest
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.services.page_interest_derivation import (
    derive_page_interests,
    merge_page_interests,
)
from kiseki.domain.shared.settings import PageSettings
from kiseki.domain.web.reading import PageReading

WHEN = datetime(2026, 9, 1, tzinfo=UTC)


def _reading(
    reference: str,
    day: date,
    labels: tuple[str, ...],
    category: str = "reading",
    refused: str | None = None,
) -> PageReading:
    return PageReading(
        reference=reference,
        day=day,
        category=category,
        labels=labels,
        model="demo",
        created_at=WHEN,
        refused=refused,
    )


def _days(count: int, label: str = "raft") -> list[PageReading]:
    return [_reading("page:a", date(2026, 3, 1 + index), (label,)) for index in range(count)]


def test_a_page_opened_on_three_days_is_still_a_passing_thought() -> None:
    """Three is what a note needs plus one; a page needs more, and the
    default is the export gate's three plus one."""
    assert derive_page_interests(_days(3)) == ()


def test_a_page_opened_on_four_days_is_a_subject_with_its_own_kind() -> None:
    interests = derive_page_interests(_days(4))
    assert [interest.topic for interest in interests] == ["raft"]
    assert interests[0].evidence[0].kind is EvidenceKind.PAGE
    assert interests[0].evidence[0].reference == "page:a"


def test_the_threshold_is_the_owner_s() -> None:
    interests = derive_page_interests(_days(2), PageSettings(min_days=2, confidence_full_days=4))
    assert [interest.topic for interest in interests] == ["raft"]
    assert interests[0].confidence == pytest.approx(0.5)


def test_confidence_saturates_later_than_a_note_s() -> None:
    interests = derive_page_interests(_days(5))
    assert interests[0].confidence == pytest.approx(0.5)


def test_two_pages_on_one_day_are_still_one_day() -> None:
    readings = [
        _reading("page:a", date(2026, 3, 1), ("raft",)),
        _reading("page:b", date(2026, 3, 1), ("raft",)),
        _reading("page:c", date(2026, 3, 2), ("raft",)),
        _reading("page:d", date(2026, 3, 3), ("raft",)),
    ]
    assert derive_page_interests(readings) == ()


def test_an_unlabelled_category_contributes_nothing() -> None:
    """The type refuses labels on these already; the second lock."""
    readings = [
        _reading("page:a", date(2026, 3, 1 + index), (), category="news") for index in range(6)
    ]
    assert derive_page_interests(readings) == ()


def test_a_refused_reading_says_nothing() -> None:
    readings = [
        _reading("page:a", date(2026, 3, 1 + index), ("raft",), refused="declined")
        for index in range(6)
    ]
    assert derive_page_interests(readings) == ()


def test_the_photographs_keep_their_reading() -> None:
    photograph = Interest(
        topic="raft",
        score=1.0,
        confidence=0.9,
        evidence=(
            InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference="caption:x", observed_at=WHEN),
        ),
        first_seen=WHEN,
        last_seen=WHEN,
    )
    profile = Profile(generated_at=WHEN, interests=(photograph,))
    merged = merge_page_interests(profile, derive_page_interests(_days(6)))
    assert merged.interests[0].evidence[0].kind is EvidenceKind.PHOTOGRAPH
    assert len(merged.interests) == 1


def test_a_page_adds_what_nothing_else_saw() -> None:
    profile = Profile(generated_at=WHEN, interests=())
    merged = merge_page_interests(profile, derive_page_interests(_days(4)))
    assert [interest.topic for interest in merged.interests] == ["raft"]


def test_a_page_subject_that_is_admitted_has_already_cleared_the_export_gate() -> None:
    """Four days sits above the gate's three readings on purpose. The
    first draft of ADR-0089 claimed the opposite, that page interests
    could not leave alone; this is what is actually true."""
    from kiseki.application.exporting import MIN_EXPORT_CONFIDENCE, MIN_EXPORT_EVIDENCE

    interest = derive_page_interests(_days(4))[0]
    assert len(interest.evidence) >= MIN_EXPORT_EVIDENCE
    assert interest.confidence >= MIN_EXPORT_CONFIDENCE


def test_a_saturation_below_the_admission_is_refused() -> None:
    with pytest.raises(ValueError, match="saturate"):
        PageSettings(min_days=4, confidence_full_days=3)
