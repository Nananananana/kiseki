"""What leaves is thinner than what is held, and the gate is evidence."""

from datetime import UTC, date, datetime

from kiseki.application.exporting import (
    MIN_EXPORT_CONFIDENCE,
    MIN_EXPORT_EVIDENCE,
    interest_export,
)
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence, Profile
from kiseki.domain.lifecycle import LifecycleReport, LifecycleStage, TopicLifecycle

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)
TODAY = date(2026, 8, 29)


def _interest(topic: str, evidence: int, confidence: float = 0.8) -> Interest:
    return Interest(
        topic=topic,
        score=0.6,
        confidence=confidence,
        evidence=tuple(
            InterestEvidence(
                kind=EvidenceKind.PHOTOGRAPH,
                reference=f"caption:{topic}-{index}",
                observed_at=WHEN,
            )
            for index in range(evidence)
        ),
        first_seen=WHEN,
        last_seen=WHEN,
    )


def _profile(*interests: Interest) -> Profile:
    return Profile(generated_at=WHEN, interests=interests)


def test_a_topic_seen_often_enough_leaves() -> None:
    document = interest_export(_profile(_interest("ramen", 5)), None, TODAY)
    assert [item["topic"] for item in document["interests"]] == ["ramen"]


def test_a_topic_seen_once_stays_home() -> None:
    """A word from a single photograph of a document is a coincidence."""
    document = interest_export(_profile(_interest("lesion", 1)), None, TODAY)
    assert document["interests"] == []


def test_the_threshold_is_where_it_says_it_is() -> None:
    below = interest_export(_profile(_interest("pill", MIN_EXPORT_EVIDENCE - 1)), None, TODAY)
    at = interest_export(_profile(_interest("pill", MIN_EXPORT_EVIDENCE)), None, TODAY)
    assert below["interests"] == []
    assert len(at["interests"]) == 1


def test_a_reading_the_library_half_believes_stays_home() -> None:
    document = interest_export(
        _profile(_interest("blur", 9, confidence=MIN_EXPORT_CONFIDENCE - 0.01)),
        None,
        TODAY,
    )
    assert document["interests"] == []


def test_a_place_never_leaves_however_often_it_is_seen() -> None:
    document = interest_export(_profile(_interest("place:34.78,135.46", 40)), None, TODAY)
    assert document["interests"] == []


def test_a_stage_without_its_interest_does_not_leave_either() -> None:
    """The stages named topics the interests no longer carry."""
    lifecycle = LifecycleReport(
        oldest_at=WHEN,
        latest_at=WHEN,
        lifecycles=(
            TopicLifecycle(
                topic="ramen",
                stage=LifecycleStage.STABLE,
                strength=0.6,
                baseline=0.6,
                seen_profiles=4,
            ),
            TopicLifecycle(
                topic="lesion",
                stage=LifecycleStage.NEW,
                strength=0.2,
                baseline=0.0,
                seen_profiles=1,
            ),
        ),
    )
    document = interest_export(
        _profile(_interest("ramen", 5), _interest("lesion", 1)), lifecycle, TODAY
    )
    assert [item["topic"] for item in document["stages"]] == ["ramen"]


def test_the_schema_is_unchanged() -> None:
    document = interest_export(_profile(_interest("ramen", 5)), None, TODAY)
    assert document["schema"] == "kiseki-interest-export"
    assert document["version"] == 1
    assert set(document) == {"schema", "version", "exported_on", "interests", "stages"}
