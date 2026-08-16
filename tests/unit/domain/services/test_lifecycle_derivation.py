"""Where each topic stands in its life, read from the whole history."""

from datetime import UTC, datetime, timedelta

from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.lifecycle import LifecycleStage
from kiseki.domain.services.lifecycle_derivation import derive_lifecycles

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


def _stage_of(report, topic: str) -> LifecycleStage:
    return next(item.stage for item in report.lifecycles if item.topic == topic)


def test_one_profile_is_not_enough():
    assert derive_lifecycles((_profile(0),)) is None


def test_a_close_pair_is_not_enough():
    assert derive_lifecycles((_profile(0), _profile(5))) is None


def test_a_first_appearance_is_new():
    report = derive_lifecycles((_profile(0), _profile(20, _interest("onsen"))))
    assert report is not None
    assert _stage_of(report, "onsen") is LifecycleStage.NEW


def test_a_gap_and_a_comeback_is_returned():
    history = (
        _profile(0, _interest("skiing")),
        _profile(30),
        _profile(60, _interest("skiing")),
    )
    report = derive_lifecycles(history)
    assert report is not None
    assert _stage_of(report, "skiing") is LifecycleStage.RETURNED


def test_growth_is_growing():
    history = (
        _profile(0, _interest("museum", 0.5, 0.4)),
        _profile(20, _interest("museum", 0.9, 0.5)),
    )
    report = derive_lifecycles(history)
    assert report is not None
    assert _stage_of(report, "museum") is LifecycleStage.GROWING


def test_small_movement_is_stable():
    history = (
        _profile(0, _interest("museum", 0.5, 0.40)),
        _profile(20, _interest("museum", 0.5, 0.46)),
    )
    report = derive_lifecycles(history)
    assert report is not None
    assert _stage_of(report, "museum") is LifecycleStage.STABLE


def test_loss_is_declining():
    history = (
        _profile(0, _interest("museum", 0.9, 0.5)),
        _profile(20, _interest("museum", 0.5, 0.4)),
    )
    report = derive_lifecycles(history)
    assert report is not None
    assert _stage_of(report, "museum") is LifecycleStage.DECLINING


def test_a_faded_topic_is_dormant():
    report = derive_lifecycles((_profile(0, _interest("skiing")), _profile(20)))
    assert report is not None
    item = next(item for item in report.lifecycles if item.topic == "skiing")
    assert item.stage is LifecycleStage.DORMANT
    assert item.strength == 0.0


def test_a_long_gone_topic_is_still_dormant():
    history = (
        _profile(0, _interest("skiing")),
        _profile(30, _interest("museum")),
        _profile(60, _interest("museum")),
    )
    report = derive_lifecycles(history)
    assert report is not None
    assert _stage_of(report, "skiing") is LifecycleStage.DORMANT


def test_interesting_stages_come_first():
    history = (
        _profile(0, _interest("museum", 0.5, 0.40)),
        _profile(
            20,
            _interest("museum", 0.5, 0.42),
            _interest("onsen", 0.8, 0.9),
        ),
    )
    report = derive_lifecycles(history)
    assert report is not None
    assert [item.topic for item in report.lifecycles] == ["onsen", "museum"]


def test_seen_profiles_counts_the_appearances():
    history = (
        _profile(0, _interest("museum")),
        _profile(30, _interest("museum")),
        _profile(60, _interest("museum")),
    )
    report = derive_lifecycles(history)
    assert report is not None
    item = next(item for item in report.lifecycles if item.topic == "museum")
    assert item.seen_profiles == 3

def test_growth_carries_its_baseline():
    history = (
        _profile(0, _interest("museum", 0.5, 0.4)),
        _profile(20, _interest("museum", 0.9, 0.5)),
    )
    report = derive_lifecycles(history)
    assert report is not None
    item = next(item for item in report.lifecycles if item.topic == "museum")
    assert item.baseline == 0.5 * 0.4
    assert item.strength == 0.9 * 0.5


def test_a_new_topic_has_no_baseline():
    report = derive_lifecycles((_profile(0), _profile(20, _interest("onsen"))))
    assert report is not None
    item = next(item for item in report.lifecycles if item.topic == "onsen")
    assert item.baseline == 0.0
