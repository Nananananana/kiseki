"""Stay-point detection, as the trajectory literature defines it.

The canonical algorithm for turning a trace into places somebody
stayed: Li, Zheng, Xie, Chen, Ma and Wang, *Mining user similarity
based on location history* (ACM GIS 2008), and used throughout the
GeoLife work that followed. It is the thing most other tools mean when
they say "stay point", so it is here to be **comparable** as much as
to be used.

Implemented from the published description rather than adapted from
anyone's code, which is what lets it sit in a package that declares no
dependency at all.

    from each unassigned photograph i, extend j forward while every
    p[j] is within `stay_radius` of **p[i]**; if the span from i to
    the last such j reaches `min_duration`, that run is a stay point;
    continue from the photograph after it.

**One difference from `sequential`, and it is the whole point.** The
radius is measured from the **anchor** -- the first photograph of the
run -- and never moves. `sequential` measures from the centre of the
group so far, which follows the photographs as they wander. So this
detector cannot walk away from where a stay began: a slow drift across
a park ends the stay here and continues it there.

That makes this the stricter of the two about *place*, and the more
literal about *what a stay is*. Neither is more correct. Which one a
reader wants depends on whether "I was at the park" or "I was at the
bench by the pond" is the answer they were looking for.

**Where it is weak.** A stay that begins at the edge of a large site
and moves to the middle is cut in two, even though a person would call
it one visit -- the mirror image of `sequential`'s weakness. And a run
is extended only while *every* photograph is inside the radius, so one
stray coordinate in the middle of an afternoon ends the stay there.
"""

from collections.abc import Sequence

from kiseki.domain.photo.observation import PhotoObservation
from kiseki.domain.services.detectors.shared import (
    Located,
    StopExtraction,
    assemble,
    located_and_unlocated,
)
from kiseki.domain.shared.settings import StopSettings

NAME = "staypoint"


def detect(located: Sequence[Located], settings: StopSettings) -> list[list[Located]]:
    groups: list[list[Located]] = []
    index = 0
    while index < len(located):
        anchor = located[index]
        ahead = index + 1
        while ahead < len(located):
            candidate = located[ahead]
            if candidate.captured_at - located[ahead - 1].captured_at > settings.max_gap:
                break
            if anchor.location.distance_to(candidate.location) > settings.stay_radius:
                break
            ahead += 1
        groups.append(list(located[index:ahead]))
        index = ahead
    return groups


def extract(observations: Sequence[PhotoObservation], settings: StopSettings) -> StopExtraction:
    located, unlocated = located_and_unlocated(observations)
    stops, in_transit = assemble(detect(located, settings), settings)
    return StopExtraction(stops, in_transit, unlocated)
