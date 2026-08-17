"""Discovery ranks by novelty and importance; confidence never ranks."""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.domain.discovery import Discovery, DiscoveryFeed
from kiseki.domain.insight import InsightKind
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.services.discovering import derive_discoveries

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


def test_one_profile_is_not_enough():
    assert derive_discoveries((_profile(0),)) is None


def test_importance_is_magnitude_scaled_by_evidence():
    history = (
        _profile(0, _interest("museum", 0.5, 0.4)),
        _profile(20, _interest("museum", 0.9, 0.5)),
    )
    feed = derive_discoveries(history)
    assert feed is not None
    entry = next(item for item in feed.entries if item.topic == "museum")
    assert entry.importance == pytest.approx(0.25 * (1 / 6))


def test_confidence_never_ranks():
    history = (
        _profile(0),
        _profile(
            20,
            _interest("onsen", 0.4, 0.9),
            _interest("ramen", 0.9, 0.1),
        ),
    )
    feed = derive_discoveries(history)
    assert feed is not None
    assert [item.topic for item in feed.entries] == ["ramen", "onsen"]


def test_the_feed_is_capped():
    latest = [_interest(f"topic{index:02d}") for index in range(12)]
    feed = derive_discoveries((_profile(0), _profile(20, *latest)))
    assert feed is not None
    assert len(feed.entries) == 10


def test_an_evidence_less_finding_sinks():
    history = (
        _profile(0, _interest("skiing", 0.6, 0.5)),
        _profile(20, _interest("onsen", 0.8, 0.9)),
    )
    feed = derive_discoveries(history)
    assert feed is not None
    assert feed.entries[0].kind is InsightKind.NEW
    dormant = next(item for item in feed.entries if item.kind is InsightKind.DORMANT)
    assert dormant.importance == 0.0


def test_importance_bounds_are_enforced():
    with pytest.raises(ValueError):
        Discovery(
            topic="onsen",
            kind=InsightKind.NEW,
            magnitude=0.5,
            confidence=0.5,
            evidence=(),
            novelty=1.0,
            importance=1.5,
        )


def test_the_feed_orders_by_novelty_times_importance():
    feed = DiscoveryFeed(oldest_at=BASE, latest_at=BASE, entries=())
    assert feed.entries == ()
