"""Derives findings from the kept history, deterministically.

Built on the lifecycle (ADR-0042), which is built on the trend
(ADR-0025): the stages say what happened, the trend says by how
much, and the latest profile supplies the grounding -- confidence
and evidence are reused from the interests, never recomputed and
never guessed. A long-gone dormant topic and a weak stable one are
inventory, not findings, and produce no insight. No model is
consulted; a model may later narrate these, never add to them.
See ADR-0043.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from kiseki.domain.caption.themes import Theme
from kiseki.domain.insight import (
    Insight,
    InsightDirection,
    InsightKind,
    InsightReport,
)
from kiseki.domain.interests import Profile
from kiseki.domain.lifecycle import LifecycleStage, TopicLifecycle
from kiseki.domain.services.lifecycle_derivation import derive_lifecycles
from kiseki.domain.services.trend_derivation import derive_trend
from kiseki.domain.trends import TopicTrend

NOVELTY = {
    InsightKind.NEW: 1.0,
    InsightKind.RETURNED: 0.85,
    InsightKind.RISING: 0.7,
    InsightKind.DECLINING: 0.6,
    InsightKind.DORMANT: 0.4,
    InsightKind.ENDURING: 0.3,
}
"""How likely a finding is to be news to its own subject; fixed per
kind, so the ordering is arithmetic and a test can pin it."""

ENDURING_STRENGTH = 0.6
"""A stable topic below this strength is inventory, not a finding."""

EVIDENCE_CAP = 6


def derive_insights(
    history: Sequence[Profile],
    themes: Sequence[Theme] = (),
) -> InsightReport | None:
    """Every current finding, or None while the history is too short."""
    lifecycle = derive_lifecycles(history, themes)
    if lifecycle is None:
        return None
    trend = derive_trend(history, themes)
    if trend is None:
        return None
    latest = history[-1]
    members_of = {theme.name: frozenset(theme.members) for theme in themes}
    moved_by_topic = {item.topic: item for item in trend.trends}

    findings: list[Insight] = []
    for item in lifecycle.lifecycles:
        classified = _classify(item, moved_by_topic.get(item.topic))
        if classified is None:
            continue
        kind, direction, magnitude = classified
        first, last, confidence, evidence = _grounding(item.topic, latest, members_of)
        findings.append(
            Insight(
                topic=item.topic,
                kind=kind,
                direction=direction,
                magnitude=magnitude,
                first_seen=first,
                last_seen=last,
                confidence=confidence,
                evidence=evidence,
                novelty=NOVELTY[kind],
                derived_from=(
                    "trend",
                    "lifecycle",
                    f"profile:{latest.generated_at.isoformat()}",
                ),
            )
        )

    ordered = sorted(
        findings,
        key=lambda finding: (-finding.novelty, -finding.magnitude, finding.topic),
    )
    return InsightReport(lifecycle.oldest_at, lifecycle.latest_at, tuple(ordered))


def _classify(
    item: TopicLifecycle, moved: TopicTrend | None
) -> tuple[InsightKind, InsightDirection, float] | None:
    if item.stage is LifecycleStage.NEW:
        return (InsightKind.NEW, InsightDirection.UP, item.strength)
    if item.stage is LifecycleStage.RETURNED:
        return (InsightKind.RETURNED, InsightDirection.UP, item.strength)
    if item.stage is LifecycleStage.GROWING and moved is not None:
        return (InsightKind.RISING, InsightDirection.UP, moved.strength - moved.baseline)
    if item.stage is LifecycleStage.DECLINING and moved is not None:
        return (
            InsightKind.DECLINING,
            InsightDirection.DOWN,
            moved.baseline - moved.strength,
        )
    if item.stage is LifecycleStage.DORMANT:
        if moved is None:
            return None
        return (InsightKind.DORMANT, InsightDirection.DOWN, moved.baseline)
    if item.stage is LifecycleStage.STABLE and item.strength >= ENDURING_STRENGTH:
        return (InsightKind.ENDURING, InsightDirection.FLAT, item.strength)
    return None


def _grounding(
    topic: str,
    latest: Profile,
    members_of: Mapping[str, frozenset[str]],
) -> tuple[datetime | None, datetime | None, float, tuple[str, ...]]:
    members = members_of.get(topic, frozenset((topic,)))
    matched = [
        interest
        for interest in latest.interests
        if interest.topic == topic or interest.topic in members
    ]
    if not matched:
        return (None, None, 0.0, ())
    references = sorted(
        {evidence.reference for interest in matched for evidence in interest.evidence}
    )
    return (
        min(interest.first_seen for interest in matched),
        max(interest.last_seen for interest in matched),
        max(interest.confidence for interest in matched),
        tuple(references[:EVIDENCE_CAP]),
    )
