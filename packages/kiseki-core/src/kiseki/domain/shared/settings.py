"""Thresholds that govern how journeys are reconstructed.

These are settings rather than constants on purpose. Values tuned against one
person's photographs would not survive contact with anyone else's, so the
defaults below are a starting point and every caller can replace them.
"""

from dataclasses import dataclass
from datetime import timedelta

from kiseki.domain.shared.geo import Distance
from kiseki.domain.shared.speed import Speed

DEFAULT_STAY_RADIUS = Distance(300)
DEFAULT_DRIFT_SPEED = Speed.from_kilometers_per_hour(1.5)
DEFAULT_MAX_GAP = timedelta(minutes=90)
DEFAULT_MIN_DURATION = timedelta(minutes=10)
DEFAULT_MIN_PHOTOGRAPHS = 5
DEFAULT_MAX_ABSENCE = timedelta(hours=8)


@dataclass(frozen=True)
class StopSettings:
    """How to tell a stay from a journey.

    stay_radius
        How far a photograph may sit from the centre of a stay and still belong
        to it. Covers consumer GPS wander and moving about within a site.
    drift_speed
        Movement at or below this speed does not end a stay. Set below walking
        pace, so strolling through a large park remains one visit.
    max_gap
        A silence longer than this ends the stay regardless of distance.
    min_duration
        Below this, a group is treated as passing through rather than staying.
    min_photographs
        A group with at least this many photographs is a stay even if brief.
    """

    stay_radius: Distance = DEFAULT_STAY_RADIUS
    drift_speed: Speed = DEFAULT_DRIFT_SPEED
    max_gap: timedelta = DEFAULT_MAX_GAP
    min_duration: timedelta = DEFAULT_MIN_DURATION
    min_photographs: int = DEFAULT_MIN_PHOTOGRAPHS

    def __post_init__(self) -> None:
        if self.max_gap <= timedelta(0):
            raise ValueError("max_gap must be positive")
        if self.min_duration < timedelta(0):
            raise ValueError("min_duration cannot be negative")
        if self.min_photographs < 1:
            raise ValueError("min_photographs must be at least 1")


@dataclass(frozen=True)
class OutingSettings:
    """How to tell one outing from the next.

    max_absence
        The longest silence an outing may contain. Used when no anchor is known,
        and as a safety net when someone leaves and returns without photographing
        home. Set at eight hours so that a night's sleep away from home ends the
        outing, which is what v0.1 wants; grouping those back together is what
        Trip does in v1.0.
    """

    max_absence: timedelta = DEFAULT_MAX_ABSENCE

    def __post_init__(self) -> None:
        if self.max_absence <= timedelta(0):
            raise ValueError("max_absence must be positive")
