"""Ranks the findings by novelty and importance, deterministically.

importance = magnitude scaled by how much evidence remains, saturating
at IMPORTANCE_SATURATION references: a big move on thin evidence is
not yet worth the owner's attention, and a finding with no evidence
left (a dormant topic) sinks to zero. The rank is novelty times
importance; confidence is shown, never ranked on. See ADR-0048.
"""

from __future__ import annotations

from collections.abc import Sequence

from kiseki.domain.caption.themes import Theme
from kiseki.domain.discovery import Discovery, DiscoveryFeed
from kiseki.domain.interests import Profile
from kiseki.domain.services.insight_derivation import derive_insights

FEED_SIZE = 10
IMPORTANCE_SATURATION = 6


def derive_discoveries(
    history: Sequence[Profile],
    themes: Sequence[Theme] = (),
) -> DiscoveryFeed | None:
    """The feed, or None while the history is too short."""
    insights = derive_insights(history, themes)
    if insights is None:
        return None
    entries = [
        Discovery(
            topic=item.topic,
            kind=item.kind,
            magnitude=item.magnitude,
            confidence=item.confidence,
            evidence=item.evidence,
            novelty=item.novelty,
            importance=min(1.0, item.magnitude)
            * min(1.0, len(item.evidence) / IMPORTANCE_SATURATION),
        )
        for item in insights.insights
    ]
    ordered = sorted(entries, key=lambda entry: (-(entry.novelty * entry.importance), entry.topic))
    return DiscoveryFeed(insights.oldest_at, insights.latest_at, tuple(ordered[:FEED_SIZE]))
