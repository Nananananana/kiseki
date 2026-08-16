"""A comparison says what changed and shows the arithmetic behind it."""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.domain.caption.themes import Theme
from kiseki.domain.comparison import ChangeKind, Comparison, ComparisonEntry
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.services.comparing import compare_profiles

BASE = datetime(2026, 1, 1, 12, tzinfo=UTC)


def _interest(topic: str, score: float = 0.6, confidence: float = 0.5, *refs: str) -> Interest:
    evidence = tuple(
        InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference=reference, observed_at=BASE)
        for reference in (refs or ("caption:aa",))
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


def _entry(comparison: Comparison, topic: str) -> ComparisonEntry:
    return next(entry for entry in comparison.entries if entry.topic == topic)


def test_a_new_topic_appeared():
    comparison = compare_profiles(_profile(0), _profile(20, _interest("onsen", 0.8, 0.9)))
    entry = _entry(comparison, "onsen")
    assert entry.change is ChangeKind.APPEARED
    assert entry.strength_before == 0.0
    assert entry.strength_after == pytest.approx(0.72)


def test_a_lost_topic_is_gone():
    comparison = compare_profiles(_profile(0, _interest("skiing", 0.6, 0.5)), _profile(20))
    entry = _entry(comparison, "skiing")
    assert entry.change is ChangeKind.GONE
    assert entry.strength_before == pytest.approx(0.30)
    assert entry.strength_after == 0.0


def test_growth_is_stronger_with_both_strengths():
    comparison = compare_profiles(
        _profile(0, _interest("museum", 0.5, 0.4)),
        _profile(20, _interest("museum", 0.9, 0.5)),
    )
    entry = _entry(comparison, "museum")
    assert entry.change is ChangeKind.STRONGER
    assert entry.strength_before == pytest.approx(0.20)
    assert entry.strength_after == pytest.approx(0.45)


def test_loss_of_weight_is_weaker():
    comparison = compare_profiles(
        _profile(0, _interest("museum", 0.9, 0.5)),
        _profile(20, _interest("museum", 0.5, 0.4)),
    )
    assert _entry(comparison, "museum").change is ChangeKind.WEAKER


def test_small_movement_is_steady():
    comparison = compare_profiles(
        _profile(0, _interest("museum", 0.5, 0.40)),
        _profile(20, _interest("museum", 0.5, 0.46)),
    )
    assert _entry(comparison, "museum").change is ChangeKind.STEADY


def test_identical_readings_are_all_steady():
    comparison = compare_profiles(
        _profile(0, _interest("museum"), _interest("onsen")),
        _profile(20, _interest("museum"), _interest("onsen")),
    )
    assert all(entry.change is ChangeKind.STEADY for entry in comparison.entries)


def test_the_interesting_changes_come_first():
    comparison = compare_profiles(
        _profile(0, _interest("museum", 0.5, 0.4)),
        _profile(
            20,
            _interest("museum", 0.9, 0.5),
            _interest("onsen", 0.4, 0.4),
        ),
    )
    assert [entry.topic for entry in comparison.entries] == ["onsen", "museum"]


def test_the_evidence_counts_travel():
    comparison = compare_profiles(
        _profile(0, _interest("museum", 0.6, 0.5, "caption:aa", "caption:bb")),
        _profile(20, _interest("museum", 0.6, 0.5, "caption:cc")),
    )
    entry = _entry(comparison, "museum")
    assert entry.evidence_before == 2
    assert entry.evidence_after == 1


def test_the_references_come_from_the_after_side_capped():
    comparison = compare_profiles(
        _profile(0, _interest("museum", 0.6, 0.5, "caption:zz")),
        _profile(
            20,
            _interest("museum", 0.6, 0.5, "caption:dd", "caption:cc", "caption:bb", "caption:aa"),
        ),
    )
    entry = _entry(comparison, "museum")
    assert entry.evidence_refs == ("caption:aa", "caption:bb", "caption:cc")
    gone = compare_profiles(_profile(0, _interest("skiing")), _profile(20))
    assert _entry(gone, "skiing").evidence_refs == ()


def test_themes_merge_the_members():
    themes = (Theme(name="food", members=("ramen", "udon")),)
    comparison = compare_profiles(
        _profile(0, _interest("ramen", 0.5, 0.4)),
        _profile(20, _interest("udon", 0.9, 0.5)),
        themes=themes,
    )
    assert len(comparison.entries) == 1
    entry = comparison.entries[0]
    assert entry.topic == "food"
    assert entry.change is ChangeKind.STRONGER


def test_a_reversed_pair_is_refused():
    with pytest.raises(ValueError):
        compare_profiles(_profile(20), _profile(0))


def test_an_entry_needs_a_topic():
    with pytest.raises(ValueError):
        ComparisonEntry(
            topic="",
            change=ChangeKind.STEADY,
            strength_before=0.1,
            strength_after=0.1,
            evidence_before=1,
            evidence_after=1,
            evidence_refs=(),
        )
