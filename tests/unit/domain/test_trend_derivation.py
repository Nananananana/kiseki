"""The trend derivation: profiles compared through the current themes.

Theme adoption changes the topic vocabulary between old and new
profiles, so a raw comparison would read renaming as fading. Every
topic is therefore mapped through the current theme set before the
comparison; a member label is read as its theme, and a collision
keeps the strongest reading. Everything here is deterministic.
See ADR-0025.
"""

from datetime import datetime, timedelta

import pytest
from kiseki.domain.caption.themes import Theme
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.services.trend_derivation import (
    MIN_TREND_SPAN_DAYS,
    derive_trend,
)
from kiseki.domain.trends import TopicTrend, TrendDirection

BASE = datetime(2026, 6, 1, 12)

OUTDOOR = Theme(name="outdoor", members=("tree", "mountain"))


def _interest(topic: str, score: float, confidence: float) -> Interest:
    evidence = (
        InterestEvidence(
            kind=EvidenceKind.PHOTOGRAPH,
            reference=f"caption:{topic}",
            observed_at=BASE,
        ),
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
    return Profile(generated_at=BASE + timedelta(days=days), interests=interests)


class TestHistoryRequirements:
    def test_no_history_yields_no_trend(self) -> None:
        assert derive_trend(()) is None

    def test_one_profile_is_not_yet_a_trend(self) -> None:
        assert derive_trend((_profile(0),)) is None

    def test_a_baseline_closer_than_the_minimum_span_is_not_used(self) -> None:
        history = (_profile(0), _profile(MIN_TREND_SPAN_DAYS - 1))
        assert derive_trend(history) is None

    def test_the_minimum_span_itself_is_enough(self) -> None:
        history = (_profile(0), _profile(MIN_TREND_SPAN_DAYS))
        assert derive_trend(history) is not None

    def test_the_baseline_is_the_most_recent_eligible_profile(self) -> None:
        """Not the oldest: the question is what changed lately."""
        old = _profile(0, _interest("museum", 0.4, 0.5))
        eligible = _profile(30, _interest("museum", 0.8, 0.5))
        latest = _profile(60, _interest("museum", 0.8, 0.5))

        report = derive_trend((old, eligible, latest))

        assert report is not None
        assert report.baseline_at == eligible.generated_at
        assert report.latest_at == latest.generated_at
        (trend,) = report.trends
        assert trend.direction is TrendDirection.STEADY

    def test_two_empty_profiles_yield_an_empty_report(self) -> None:
        """No movement to report is itself a finding, not an error."""
        report = derive_trend((_profile(0), _profile(20)))
        assert report is not None
        assert report.trends == ()


class TestDirections:
    def test_a_topic_only_in_the_latest_is_new(self) -> None:
        report = derive_trend((_profile(0), _profile(20, _interest("onsen", 0.5, 0.4))))
        assert report is not None
        (trend,) = report.trends
        assert trend.direction is TrendDirection.NEW
        assert trend.baseline == 0.0
        assert trend.strength == pytest.approx(0.5 * 0.4)

    def test_a_topic_only_in_the_baseline_has_faded(self) -> None:
        report = derive_trend((_profile(0, _interest("skiing", 0.5, 0.4)), _profile(20)))
        assert report is not None
        (trend,) = report.trends
        assert trend.direction is TrendDirection.FADED
        assert trend.strength == 0.0
        assert trend.baseline == pytest.approx(0.5 * 0.4)

    def test_growth_beyond_the_delta_is_rising(self) -> None:
        history = (
            _profile(0, _interest("museum", 0.5, 0.4)),
            _profile(20, _interest("museum", 0.9, 0.5)),
        )
        report = derive_trend(history)
        assert report is not None
        assert report.trends[0].direction is TrendDirection.RISING

    def test_loss_beyond_the_delta_is_declining(self) -> None:
        history = (
            _profile(0, _interest("museum", 0.9, 0.5)),
            _profile(20, _interest("museum", 0.5, 0.4)),
        )
        report = derive_trend(history)
        assert report is not None
        assert report.trends[0].direction is TrendDirection.DECLINING

    def test_movement_within_the_delta_is_steady(self) -> None:
        history = (
            _profile(0, _interest("museum", 0.5, 0.40)),
            _profile(20, _interest("museum", 0.5, 0.46)),
        )
        report = derive_trend(history)
        assert report is not None
        assert report.trends[0].direction is TrendDirection.STEADY


class TestThemeMapping:
    def test_a_member_topic_is_read_as_its_theme(self) -> None:
        """A pre-theme history stays comparable to a themed present."""
        history = (
            _profile(0, _interest("tree", 0.6, 0.5)),
            _profile(20, _interest("outdoor", 0.6, 0.5)),
        )
        report = derive_trend(history, themes=(OUTDOOR,))
        assert report is not None
        (trend,) = report.trends
        assert trend.topic == "outdoor"
        assert trend.direction is TrendDirection.STEADY

    def test_colliding_members_keep_the_strongest(self) -> None:
        history = (
            _profile(
                0,
                _interest("tree", 0.6, 0.5),
                _interest("mountain", 0.9, 0.8),
            ),
            _profile(20, _interest("outdoor", 0.9, 0.8)),
        )
        report = derive_trend(history, themes=(OUTDOOR,))
        assert report is not None
        (trend,) = report.trends
        assert trend.baseline == pytest.approx(0.9 * 0.8)
        assert trend.direction is TrendDirection.STEADY

    def test_a_topic_outside_every_theme_speaks_for_itself(self) -> None:
        history = (
            _profile(0, _interest("place:35.00000,135.00000", 0.6, 0.5)),
            _profile(20, _interest("place:35.00000,135.00000", 0.6, 0.5)),
        )
        report = derive_trend(history, themes=(OUTDOOR,))
        assert report is not None
        assert report.trends[0].topic == "place:35.00000,135.00000"


class TestOrdering:
    def test_the_largest_movement_comes_first(self) -> None:
        history = (
            _profile(0, _interest("museum", 0.5, 0.40)),
            _profile(
                20,
                _interest("museum", 0.5, 0.42),
                _interest("onsen", 0.8, 0.9),
            ),
        )
        report = derive_trend(history)
        assert report is not None
        assert [trend.topic for trend in report.trends] == ["onsen", "museum"]


class TestTopicTrend:
    def test_delta_is_strength_minus_baseline(self) -> None:
        trend = TopicTrend(
            topic="onsen",
            direction=TrendDirection.RISING,
            strength=0.5,
            baseline=0.3,
        )
        assert trend.delta == pytest.approx(0.2)
