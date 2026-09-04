"""The detector this library was built on: proximity, then drift.

Walk the photographs in time order and ask of each one whether it
continues the group being built. Two signals decide. Proximity to the
**centre of the group so far** handles GPS wander and moving about a
site. Speed since the previous photograph handles the case where
somebody drifts gradually across a large area, which proximity alone
would split.

Its defaults were checked against a real photo library; ADR-0006 has
what was measured. It is the default detector and the only one whose
numbers came from anybody's actual photographs.

**Where it is weak.** The centroid moves as the group grows, so a long
stay that wanders can walk its own centre away from where it started
-- a slow enough drift never triggers either rule and the whole
afternoon becomes one stop. And because it is strictly sequential, a
place left and returned to an hour later is two stops, which is
usually right and is not always what a reader means by *how often do I
go there*.
"""

from collections.abc import Sequence

from kiseki.domain.photo.observation import PhotoObservation
from kiseki.domain.services.detectors.shared import (
    Located,
    StopExtraction,
    assemble,
    centroid,
    located_and_unlocated,
)
from kiseki.domain.shared.settings import StopSettings
from kiseki.domain.shared.speed import Speed

NAME = "sequential"


def _continues(group: Sequence[Located], candidate: Located, settings: StopSettings) -> bool:
    previous = group[-1]
    gap = candidate.captured_at - previous.captured_at

    if gap > settings.max_gap:
        return False
    if centroid(group).distance_to(candidate.location) <= settings.stay_radius:
        return True
    if gap.total_seconds() <= 0:
        # Speed.between refuses a zero duration, and two photographs
        # sharing a timestamp are ordinary in a merged library.
        return False

    travelled = previous.location.distance_to(candidate.location)
    return Speed.between(travelled, gap) <= settings.drift_speed


def detect(located: Sequence[Located], settings: StopSettings) -> list[list[Located]]:
    groups: list[list[Located]] = []
    for item in located:
        if groups and _continues(groups[-1], item, settings):
            groups[-1].append(item)
        else:
            groups.append([item])
    return groups


def extract(observations: Sequence[PhotoObservation], settings: StopSettings) -> StopExtraction:
    located, unlocated = located_and_unlocated(observations)
    stops, in_transit = assemble(detect(located, settings), settings)
    return StopExtraction(stops, in_transit, unlocated)
