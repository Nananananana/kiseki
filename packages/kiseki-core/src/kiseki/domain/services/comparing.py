"""Compares two readings, deterministically, with reasons attached.

Per mapped topic (themes expand to their members, as everywhere),
the strength is the strongest member's score times confidence, the
evidence count is the total, and the change is arithmetic: appeared,
gone, stronger or weaker past the trend's own delta (ADR-0025), or
steady. The references shown come from the after side, capped, so a
judgement can be walked back to evidence. No model is consulted.
See ADR-0045.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from kiseki.domain.caption.themes import Theme
from kiseki.domain.comparison import ChangeKind, Comparison, ComparisonEntry
from kiseki.domain.interests import Profile
from kiseki.domain.services.trend_derivation import TREND_DELTA

REFERENCE_CAP = 3

_CHANGE_RANK = {
    ChangeKind.APPEARED: 0,
    ChangeKind.GONE: 1,
    ChangeKind.STRONGER: 2,
    ChangeKind.WEAKER: 3,
    ChangeKind.STEADY: 4,
}


def compare_profiles(
    before: Profile,
    after: Profile,
    themes: Sequence[Theme] = (),
) -> Comparison:
    """Every topic's change between the two readings, the loudest first."""
    if before.generated_at > after.generated_at:
        raise ValueError("compare expects the earlier reading first")
    mapping = {member: theme.name for theme in themes for member in theme.members}
    before_view = _by_topic(before, mapping)
    after_view = _by_topic(after, mapping)

    entries: list[ComparisonEntry] = []
    for topic in sorted(set(before_view) | set(after_view)):
        strength_before, evidence_before, _refs = before_view.get(topic, (0.0, 0, ()))
        strength_after, evidence_after, refs = after_view.get(topic, (0.0, 0, ()))
        entries.append(
            ComparisonEntry(
                topic=topic,
                change=_change(
                    topic in before_view, topic in after_view, strength_after - strength_before
                ),
                strength_before=strength_before,
                strength_after=strength_after,
                evidence_before=evidence_before,
                evidence_after=evidence_after,
                evidence_refs=refs[:REFERENCE_CAP],
            )
        )

    ordered = sorted(
        entries,
        key=lambda entry: (
            _CHANGE_RANK[entry.change],
            -abs(entry.strength_after - entry.strength_before),
            entry.topic,
        ),
    )
    return Comparison(before.generated_at, after.generated_at, tuple(ordered))


def _change(in_before: bool, in_after: bool, delta: float) -> ChangeKind:
    if not in_before:
        return ChangeKind.APPEARED
    if not in_after:
        return ChangeKind.GONE
    if delta > TREND_DELTA:
        return ChangeKind.STRONGER
    if delta < -TREND_DELTA:
        return ChangeKind.WEAKER
    return ChangeKind.STEADY


def _by_topic(
    profile: Profile, mapping: Mapping[str, str]
) -> dict[str, tuple[float, int, tuple[str, ...]]]:
    strengths: dict[str, float] = {}
    counts: dict[str, int] = {}
    references: dict[str, set[str]] = {}
    for interest in profile.interests:
        topic = mapping.get(interest.topic, interest.topic)
        strengths[topic] = max(strengths.get(topic, 0.0), interest.score * interest.confidence)
        counts[topic] = counts.get(topic, 0) + len(interest.evidence)
        gathered = references.setdefault(topic, set())
        for evidence in interest.evidence:
            gathered.add(evidence.reference)
    return {
        topic: (strengths[topic], counts[topic], tuple(sorted(references[topic])))
        for topic in strengths
    }
