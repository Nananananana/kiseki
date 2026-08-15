"""Reads the drift between two kept profiles.

The vocabulary of a profile is not stable: theme adoption replaced
member labels with theme names, and a raw comparison across that
change would read renaming as fading. Every topic is therefore
mapped through the current theme set before the comparison; a member
label is read as its theme, and a collision keeps the strongest
reading. Everything here is deterministic. No model is consulted.
See ADR-0025.
"""

from __future__ import annotations

from collections.abc import Sequence

from kiseki.domain.caption.themes import Theme
from kiseki.domain.interests import Profile
from kiseki.domain.trends import TopicTrend, TrendDirection, TrendReport

MIN_TREND_SPAN_DAYS = 14
"""Days the baseline must precede the latest reading by. Two profiles
taken in the same week differ mostly by noise: one more outing, one
more caption. To be calibrated against the real history once it has
grown past this span."""

TREND_DELTA = 0.05
"""Movement in strength below which a topic is read as steady."""


def derive_trend(
    history: Sequence[Profile],
    themes: Sequence[Theme] = (),
) -> TrendReport | None:
    """Compare the latest profile against an old enough baseline.

    The baseline is the most recent profile generated at least
    MIN_TREND_SPAN_DAYS before the latest: the question is what
    changed lately, not what changed since the beginning. With no
    eligible baseline there is no trend, and None is that answer.
    """
    if len(history) < 2:
        return None
    latest = history[-1]
    baseline = _baseline_for(latest, history[:-1])
    if baseline is None:
        return None

    mapping = {member: theme.name for theme in themes for member in theme.members}
    before = _strengths(baseline, mapping)
    after = _strengths(latest, mapping)

    trends = tuple(
        sorted(
            (_trend_for(topic, before, after) for topic in set(before) | set(after)),
            key=lambda trend: (-abs(trend.delta), trend.topic),
        )
    )
    return TrendReport(
        baseline_at=baseline.generated_at,
        latest_at=latest.generated_at,
        trends=trends,
    )


def _baseline_for(latest: Profile, earlier: Sequence[Profile]) -> Profile | None:
    """The most recent profile old enough to compare with."""
    for candidate in reversed(earlier):
        if (latest.generated_at - candidate.generated_at).days >= MIN_TREND_SPAN_DAYS:
            return candidate
    return None


def _strengths(profile: Profile, mapping: dict[str, str]) -> dict[str, float]:
    """Topic strengths, read through the current themes.

    When several interests map to the same name, the strongest
    reading is kept: a theme is at least as present as its most
    present member.
    """
    strengths: dict[str, float] = {}
    for interest in profile.interests:
        topic = mapping.get(interest.topic, interest.topic)
        strength = interest.score * interest.confidence
        if topic not in strengths or strength > strengths[topic]:
            strengths[topic] = strength
    return strengths


def _trend_for(
    topic: str,
    before: dict[str, float],
    after: dict[str, float],
) -> TopicTrend:
    if topic not in before:
        return TopicTrend(
            topic=topic,
            direction=TrendDirection.NEW,
            strength=after[topic],
            baseline=0.0,
        )
    if topic not in after:
        return TopicTrend(
            topic=topic,
            direction=TrendDirection.FADED,
            strength=0.0,
            baseline=before[topic],
        )
    delta = after[topic] - before[topic]
    if delta > TREND_DELTA:
        direction = TrendDirection.RISING
    elif delta < -TREND_DELTA:
        direction = TrendDirection.DECLINING
    else:
        direction = TrendDirection.STEADY
    return TopicTrend(
        topic=topic,
        direction=direction,
        strength=after[topic],
        baseline=before[topic],
    )
