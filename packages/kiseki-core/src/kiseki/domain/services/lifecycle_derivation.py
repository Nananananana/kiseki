"""Reads where each topic stands, from the whole kept history.

Built on the trend (ADR-0025): the trend says how the latest reading
moved against an old enough baseline, and the history before that
baseline tells the rest -- a topic the trend calls new but the older
history already knew has returned; a topic missing from both ends but
present once is dormant. Everything is derived, deterministic, and
stored nowhere (ADR-0042). No model is consulted.
"""

from __future__ import annotations

from collections.abc import Sequence

from kiseki.domain.caption.themes import Theme
from kiseki.domain.interests import Profile
from kiseki.domain.lifecycle import LifecycleReport, LifecycleStage, TopicLifecycle
from kiseki.domain.services.theme_mapping import theme_mapping
from kiseki.domain.services.trend_derivation import derive_trend
from kiseki.domain.shared.moment import same_moment
from kiseki.domain.trends import TrendDirection

_STAGE_RANK = {
    LifecycleStage.NEW: 0,
    LifecycleStage.RETURNED: 1,
    LifecycleStage.GROWING: 2,
    LifecycleStage.DECLINING: 3,
    LifecycleStage.DORMANT: 4,
    LifecycleStage.STABLE: 5,
}

_FROM_TREND = {
    TrendDirection.RISING: LifecycleStage.GROWING,
    TrendDirection.STEADY: LifecycleStage.STABLE,
    TrendDirection.DECLINING: LifecycleStage.DECLINING,
    TrendDirection.FADED: LifecycleStage.DORMANT,
}


def derive_lifecycles(
    history: Sequence[Profile],
    themes: Sequence[Theme] = (),
) -> LifecycleReport | None:
    """Every topic's stage, or None while the history is too short."""
    trend = derive_trend(history, themes)
    if trend is None:
        return None

    mapping = theme_mapping(themes)
    presence = [_topics(profile, mapping) for profile in history]
    baseline_index = next(
        index
        for index, profile in enumerate(history)
        if same_moment(profile.generated_at, trend.baseline_at)
    )
    seen_before_baseline: set[str] = set()
    for topics in presence[:baseline_index]:
        seen_before_baseline |= topics

    lifecycles: list[TopicLifecycle] = []
    for item in trend.trends:
        if item.direction is TrendDirection.NEW:
            stage = (
                LifecycleStage.RETURNED
                if item.topic in seen_before_baseline
                else LifecycleStage.NEW
            )
        else:
            stage = _FROM_TREND[item.direction]
        lifecycles.append(
            TopicLifecycle(
                topic=item.topic,
                stage=stage,
                strength=item.strength,
                seen_profiles=_seen(item.topic, presence),
                baseline=item.baseline,
            )
        )

    covered = {item.topic for item in lifecycles}
    for topic in sorted(seen_before_baseline - covered):
        lifecycles.append(
            TopicLifecycle(
                topic=topic,
                stage=LifecycleStage.DORMANT,
                strength=0.0,
                seen_profiles=_seen(topic, presence),
            )
        )

    ordered = sorted(
        lifecycles,
        key=lambda item: (_STAGE_RANK[item.stage], -item.strength, item.topic),
    )
    return LifecycleReport(
        oldest_at=history[0].generated_at,
        latest_at=trend.latest_at,
        lifecycles=tuple(ordered),
    )


def _topics(profile: Profile, mapping: dict[str, str]) -> set[str]:
    return {mapping.get(interest.topic, interest.topic) for interest in profile.interests}


def _seen(topic: str, presence: Sequence[set[str]]) -> int:
    return sum(1 for topics in presence if topic in topics)
