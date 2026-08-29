"""The interest export: a one-way abstraction, versioned.

The only thing KISEKI ever prepares for the world outside the
machine: the profile's interests with month-level time, and the
lifecycle stages. Never raw photographs, coordinates, exact
timestamps, evidence references or any identifier -- and never a
place topic, named or not, because a list of places is a movement
history. Exporting is a deliberate act (a command), not a served
endpoint. See ADR-0047.

What leaves is also thinner than what is held, and the gate is
evidence rather than meaning. A real library exported six hundred and
ninety-five topics, and the tail of that list was the owner's work
rather than the owner: pharmaceutical software read off an office
screen, a word seen once in a photograph of a document. Choosing
which words are sensitive would mean maintaining a list of them, and
that list would be wrong for the next person. Counting evidence is a
rule instead of a taste: a topic seen three times, with confidence,
has been shown to be theirs; a topic seen once is a coincidence
wearing an interest's clothes. See ADR-0069.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from kiseki.domain.interests import Profile
from kiseki.domain.lifecycle import LifecycleReport

EXPORT_SCHEMA = "kiseki-interest-export"
EXPORT_SCHEMA_VERSION = 1

PLACE_PREFIX = "place:"

MIN_EXPORT_EVIDENCE = 3
"""How many separate readings a topic needs before it may leave.

Not a statement about what is private. A statement about what has
been shown: twice is a pair of occasions, three times is a habit of
the evidence."""

MIN_EXPORT_CONFIDENCE = 0.3
"""And how sure the library must be. A topic the library itself
half-believes is not something to send anywhere."""


def _exportable(topic: str, evidence: int, confidence: float) -> bool:
    """Whether one interest has earned its way out."""
    if topic.startswith(PLACE_PREFIX):
        return False
    if evidence < MIN_EXPORT_EVIDENCE:
        return False
    return confidence >= MIN_EXPORT_CONFIDENCE


def interest_export(
    profile: Profile,
    lifecycle: LifecycleReport | None,
    exported_on: date,
) -> dict[str, Any]:
    """The whole schema, deterministically. The single definition point."""
    kept = [
        interest
        for interest in profile.interests
        if _exportable(interest.topic, len(interest.evidence), interest.confidence)
    ]
    ordered = sorted(
        kept, key=lambda interest: (-(interest.score * interest.confidence), interest.topic)
    )
    exported = {interest.topic for interest in ordered}
    stages = (
        []
        if lifecycle is None
        else [
            {"topic": item.topic, "stage": item.stage.value}
            for item in lifecycle.lifecycles
            if item.topic in exported
        ]
    )
    return {
        "schema": EXPORT_SCHEMA,
        "version": EXPORT_SCHEMA_VERSION,
        "exported_on": exported_on.isoformat(),
        "interests": [
            {
                "topic": interest.topic,
                "score": interest.score,
                "confidence": interest.confidence,
                "first_seen": f"{interest.first_seen:%Y-%m}",
                "last_seen": f"{interest.last_seen:%Y-%m}",
            }
            for interest in ordered
        ],
        "stages": stages,
    }
