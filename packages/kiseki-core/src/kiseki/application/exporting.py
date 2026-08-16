"""The interest export: a one-way abstraction, versioned.

The only thing KISEKI ever prepares for the world outside the
machine: the profile's interests with month-level time, and the
lifecycle stages. Never raw photographs, coordinates, exact
timestamps, evidence references or any identifier -- and never a
place topic, named or not, because a list of places is a movement
history. Exporting is a deliberate act (a command), not a served
endpoint. See ADR-0047.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from kiseki.domain.interests import Profile
from kiseki.domain.lifecycle import LifecycleReport

EXPORT_SCHEMA = "kiseki-interest-export"
EXPORT_SCHEMA_VERSION = 1

PLACE_PREFIX = "place:"


def interest_export(
    profile: Profile,
    lifecycle: LifecycleReport | None,
    exported_on: date,
) -> dict[str, Any]:
    """The whole schema, deterministically. The single definition point."""
    kept = [
        interest for interest in profile.interests if not interest.topic.startswith(PLACE_PREFIX)
    ]
    ordered = sorted(
        kept, key=lambda interest: (-(interest.score * interest.confidence), interest.topic)
    )
    stages = (
        []
        if lifecycle is None
        else [
            {"topic": item.topic, "stage": item.stage.value}
            for item in lifecycle.lifecycles
            if not item.topic.startswith(PLACE_PREFIX)
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
