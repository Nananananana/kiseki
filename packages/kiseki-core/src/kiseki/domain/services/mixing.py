"""Finds the tendencies worth holding side by side.

Deterministic and tiny: every enduring finding is paired with every
rising one, the loudest products first, capped. Nothing is resolved,
nothing is judged, and no model is consulted -- the pairs exist so a
reader is never shown "rising city" without "nature stayed strong"
beside it. See ADR-0049.
"""

from __future__ import annotations

from kiseki.domain.insight import InsightKind, InsightReport
from kiseki.domain.mixed import MixedPair

MIXED_CAP = 3


def derive_mixed(report: InsightReport) -> tuple[MixedPair, ...]:
    """The held-together pairs, the loudest first."""
    holds = [item for item in report.insights if item.kind is InsightKind.ENDURING]
    rises = [item for item in report.insights if item.kind is InsightKind.RISING]
    pairs = [
        MixedPair(
            held=hold.topic,
            held_strength=hold.magnitude,
            rising=rise.topic,
            rising_magnitude=rise.magnitude,
        )
        for hold in holds
        for rise in rises
        if hold.topic != rise.topic
    ]
    ordered = sorted(
        pairs,
        key=lambda pair: (
            -(pair.held_strength * pair.rising_magnitude),
            pair.held,
            pair.rising,
        ),
    )
    return tuple(ordered[:MIXED_CAP])
