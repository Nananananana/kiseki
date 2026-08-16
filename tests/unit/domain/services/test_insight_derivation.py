"""Insights are derived from the kept history, never invented."""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.domain.insight import Insight, InsightDirection, InsightKind
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.services.insight_derivation import derive_insights

BASE = datetime(2026, 1, 1, 12, tzinfo=UTC)


def _interest(topic: str, score: float = 0.6, confidence: float = 0.5) -> Interest:
    evidence = (
        InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference="caption:aa", observed_at=BASE),
    )
    return Interest(
        topic=topic,
        score=score,
        confidence=confidence,
        evidence=evidence,
        first_seen=BASE,
        last_seen=BASE,
    )


def _profile(days: int, *interests: Interest) -> Profile:
    return Profile(generated_at=BASE + timedelta(days=days), interests=tuple(interests))


def _finding(report, topic: str) -> Insight:
    return next(item for item in report.insights if item.topic == topic)


def _raw(**overrides) -> Insight:
    values = dict(
        topic="onsen",
        kind=InsightKind.NEW,
        direction=InsightDirection.UP,
        magnitude=0.5,
        first_seen=None,
        last_seen=None,
        confidence=0.5,
        evidence=(),
        novelty=1.0,
        derived_from=("trend",),
    )
    values.update(overrides)
    return Insight(**values)


def test_one_profile_is_not_enough():
    assert derive_insights((_profile(0),)) is None


def test_a_new_topic_is_a_finding():
    report = derive_insights((_profile(0), _profile(20, _interest("onsen", 0.8, 0.9))))
    assert report is not None
    finding = _finding(report, "onsen")
    assert finding.kind is InsightKind.NEW
    assert finding.direction is InsightDirection.UP
    assert finding.novelty == 1.0
    assert finding.magnitude == pytest.approx(0.72)


def test_a_comeback_is_returned():
    history = (
        _profile(0, _interest("skiing")),
        _profile(30),
        _profile(60, _interest("skiing")),
    )
    report = derive_insights(history)
    assert report is not None
    assert _finding(report, "skiing").kind is InsightKind.RETURNED


def test_growth_is_rising_with_its_delta():
    history = (
        _profile(0, _interest("museum", 0.5, 0.4)),
        _profile(20, _interest("museum", 0.9, 0.5)),
    )
    report = derive_insights(history)
    assert report is not None
    finding = _finding(report, "museum")
    assert finding.kind is InsightKind.RISING
    assert finding.magnitude == pytest.approx(0.25)


def test_loss_is_declining():
    history = (
        _profile(0, _interest("museum", 0.9, 0.5)),
        _profile(20, _interest("museum", 0.5, 0.4)),
    )
    report = derive_insights(history)
    assert report is not None
    finding = _finding(report, "museum")
    assert finding.kind is InsightKind.DECLINING
    assert finding.direction is InsightDirection.DOWN
    assert finding.magnitude == pytest.approx(0.25)


def test_a_faded_topic_is_dormant_with_its_old_weight():
    report = derive_insights((_profile(0, _interest("skiing", 0.6, 0.5)), _profile(20)))
    assert report is not None
    finding = _finding(report, "skiing")
    assert finding.kind is InsightKind.DORMANT
    assert finding.magnitude == pytest.approx(0.30)
    assert finding.confidence == 0.0
    assert finding.evidence == ()


def test_long_gone_topics_are_not_findings():
    history = (
        _profile(0, _interest("skiing")),
        _profile(30, _interest("museum")),
        _profile(60, _interest("museum")),
    )
    report = derive_insights(history)
    assert report is not None
    assert all(item.topic != "skiing" for item in report.insights)


def test_a_strong_stable_topic_is_enduring():
    history = (
        _profile(0, _interest("museum", 0.9, 0.80)),
        _profile(20, _interest("museum", 0.9, 0.79)),
    )
    report = derive_insights(history)
    assert report is not None
    finding = _finding(report, "museum")
    assert finding.kind is InsightKind.ENDURING
    assert finding.direction is InsightDirection.FLAT


def test_a_weak_stable_topic_is_no_finding():
    history = (
        _profile(0, _interest("museum", 0.5, 0.40)),
        _profile(20, _interest("museum", 0.5, 0.42)),
    )
    report = derive_insights(history)
    assert report is not None
    assert report.insights == ()


def test_novelty_orders_the_report():
    history = (
        _profile(0, _interest("museum", 0.5, 0.4)),
        _profile(
            20,
            _interest("museum", 0.9, 0.5),
            _interest("onsen", 0.4, 0.4),
        ),
    )
    report = derive_insights(history)
    assert report is not None
    assert [item.topic for item in report.insights] == ["onsen", "museum"]


def test_grounding_comes_from_the_latest_profile():
    history = (
        _profile(0, _interest("museum", 0.5, 0.4)),
        _profile(20, _interest("museum", 0.9, 0.5)),
    )
    report = derive_insights(history)
    assert report is not None
    finding = _finding(report, "museum")
    assert finding.confidence == 0.5
    assert finding.evidence == ("caption:aa",)
    assert finding.first_seen == BASE
    assert finding.last_seen == BASE


def test_derived_from_names_the_sources():
    report = derive_insights((_profile(0), _profile(20, _interest("onsen"))))
    assert report is not None
    finding = _finding(report, "onsen")
    assert "trend" in finding.derived_from
    assert "lifecycle" in finding.derived_from
    assert any(source.startswith("profile:") for source in finding.derived_from)


def test_an_insight_needs_a_topic():
    with pytest.raises(ValueError):
        _raw(topic="")


def test_novelty_bounds_are_enforced():
    with pytest.raises(ValueError):
        _raw(novelty=0.0)
