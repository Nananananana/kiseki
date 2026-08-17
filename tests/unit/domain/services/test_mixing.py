"""Mixed evidence is stated side by side, never resolved."""

from datetime import UTC, datetime

import pytest
from kiseki.domain.insight import (
    Insight,
    InsightDirection,
    InsightKind,
    InsightReport,
)
from kiseki.domain.mixed import MixedPair
from kiseki.domain.services.mixing import derive_mixed

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _insight(topic: str, kind: InsightKind, magnitude: float) -> Insight:
    direction = InsightDirection.FLAT if kind is InsightKind.ENDURING else InsightDirection.UP
    return Insight(
        topic=topic,
        kind=kind,
        direction=direction,
        magnitude=magnitude,
        first_seen=WHEN,
        last_seen=WHEN,
        confidence=0.5,
        evidence=("caption:aa",),
        novelty=0.3 if kind is InsightKind.ENDURING else 0.7,
        derived_from=("trend", "lifecycle"),
    )


def _report(*insights: Insight) -> InsightReport:
    return InsightReport(oldest_at=WHEN, latest_at=WHEN, insights=tuple(insights))


def test_an_enduring_and_a_rising_topic_are_held_together():
    pairs = derive_mixed(
        _report(
            _insight("nature", InsightKind.ENDURING, 0.7),
            _insight("city", InsightKind.RISING, 0.3),
        )
    )
    assert pairs == (
        MixedPair(held="nature", held_strength=0.7, rising="city", rising_magnitude=0.3),
    )


def test_the_loudest_pair_comes_first():
    pairs = derive_mixed(
        _report(
            _insight("nature", InsightKind.ENDURING, 0.9),
            _insight("tea", InsightKind.ENDURING, 0.6),
            _insight("city", InsightKind.RISING, 0.4),
        )
    )
    assert [(pair.held, pair.rising) for pair in pairs] == [
        ("nature", "city"),
        ("tea", "city"),
    ]


def test_the_pairs_are_capped():
    report = _report(
        _insight("nature", InsightKind.ENDURING, 0.9),
        _insight("tea", InsightKind.ENDURING, 0.8),
        _insight("city", InsightKind.RISING, 0.4),
        _insight("ramen", InsightKind.RISING, 0.3),
    )
    assert len(derive_mixed(report)) == 3


def test_without_both_kinds_there_is_nothing_to_say():
    assert derive_mixed(_report(_insight("nature", InsightKind.ENDURING, 0.7))) == ()
    assert derive_mixed(_report(_insight("city", InsightKind.RISING, 0.3))) == ()


def test_a_pair_needs_two_topics():
    with pytest.raises(ValueError):
        MixedPair(held="nature", held_strength=0.7, rising="nature", rising_magnitude=0.3)
