"""Nothing identifying ever crosses the export boundary."""

import json
from datetime import UTC, date, datetime

from kiseki.application.exporting import interest_export
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.lifecycle import LifecycleReport, LifecycleStage, TopicLifecycle

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)
DAY = date(2026, 6, 1)


def _interest(topic: str, score: float = 0.6, confidence: float = 0.5) -> Interest:
    # Three separate readings: the export asks for that many before a
    # topic may leave (ADR-0069), and these tests are about what the
    # document does not carry rather than about how much it carries.
    evidence = tuple(
        InterestEvidence(
            kind=EvidenceKind.PHOTOGRAPH,
            reference=f"caption:aa{index}",
            observed_at=WHEN,
        )
        for index in range(3)
    )
    return Interest(
        topic=topic,
        score=score,
        confidence=confidence,
        evidence=evidence,
        first_seen=WHEN,
        last_seen=WHEN,
    )


def _profile(*interests: Interest) -> Profile:
    return Profile(generated_at=WHEN, interests=tuple(interests))


def _lifecycle(*topics: str) -> LifecycleReport:
    items = tuple(
        TopicLifecycle(topic=topic, stage=LifecycleStage.NEW, strength=0.3, seen_profiles=1)
        for topic in topics
    )
    return LifecycleReport(oldest_at=WHEN, latest_at=WHEN, lifecycles=items)


def test_the_schema_names_itself():
    document = interest_export(_profile(_interest("ramen")), None, DAY)
    assert document["schema"] == "kiseki-interest-export"
    assert document["version"] == 1
    assert document["exported_on"] == "2026-06-01"


def test_places_never_leave():
    place = "place:35.01160,135.76810"
    document = interest_export(
        _profile(_interest("ramen"), _interest(place)), _lifecycle("ramen", place), DAY
    )
    text = json.dumps(document)
    assert "place:" not in text
    assert "35.01" not in text
    assert [entry["topic"] for entry in document["interests"]] == ["ramen"]
    assert [entry["topic"] for entry in document["stages"]] == ["ramen"]


def test_no_identifiers_leave():
    document = interest_export(_profile(_interest("ramen")), None, DAY)
    text = json.dumps(document)
    assert "caption:" not in text
    assert "evidence" not in text
    assert "sha256" not in text


def test_time_is_month_grained():
    document = interest_export(_profile(_interest("ramen")), None, DAY)
    entry = document["interests"][0]
    assert entry["first_seen"] == "2026-06"
    assert entry["last_seen"] == "2026-06"


def test_the_strongest_come_first():
    document = interest_export(
        _profile(_interest("museum", 0.5, 0.4), _interest("ramen", 0.9, 0.9)), None, DAY
    )
    assert [entry["topic"] for entry in document["interests"]] == ["ramen", "museum"]


def test_no_history_means_no_stages():
    document = interest_export(_profile(_interest("ramen")), None, DAY)
    assert document["stages"] == []
