"""Density clustering, and the same thing with time in it.

Two detectors that answer a different question from the other two.
`sequential` and `staypoint` walk a trace forward and ask *is this
still the same stay*. These ask *where is this person densely
present*, and only afterwards ask when.

**DBSCAN** -- Ester, Kriegel, Sander and Xu, *A density-based
algorithm for discovering clusters* (KDD 1996). A photograph is a core
point if at least `min_photographs` photographs lie within
`stay_radius` of it; core points that reach one another are one
cluster; a photograph in no cluster is noise. Implemented from the
published description.

**ST-DBSCAN** -- Birant and Kut, *ST-DBSCAN: an algorithm for
clustering spatial-temporal data* (Data & Knowledge Engineering,
2007). The same, with a second radius in time: a neighbour must be
within `stay_radius` **and** within `max_gap`.

## Why plain DBSCAN cannot be used as it stands

A spatial cluster is a *place*, not a *visit*. Every photograph ever
taken at home is one DBSCAN cluster, spanning years, and calling that
a stop would tell a reader they had one stay lasting the length of the
library.

So each cluster is cut into visits afterwards, wherever a silence
longer than `max_gap` falls inside it -- the same rule the other two
detectors use to end a stay. What survives is DBSCAN's real advantage:
**a place is recognised as one place across the whole library**,
however many times it was left and returned to, and its shape can be
any shape rather than a circle around wherever the visit started.

ST-DBSCAN needs no such repair, because time is already in the
neighbour test. It is included precisely so the repair above can be
compared against an algorithm that does not need one.

## Where these are weak

Both are O(n squared) here: no spatial index, because an index is a
dependency and this package declares none. **That is not a few times
slower, it is three hundred.** Measured, after this paragraph first
guessed "a few times":

    5000 photographs   dbscan (here)  20.09 s
                       dbscan-indexed  0.06 s   (kiseki[clustering])

So this is a reference implementation to read beside the paper, and
the thing `dbscan-indexed` is checked against -- one specification
implemented twice, with a test asserting the two group photographs
identically. It is not what to point at a real library, and
`docs/algorithms.md` says so where a reader choosing will see it.

Both also make `min_photographs` mean something different: in the
other two it decides whether a *group* is a stay, here it also decides
whether a photograph is dense enough to be in a cluster at all. A
reader who lowers it will get more places, not just more stays.
"""

from collections.abc import Sequence
from itertools import pairwise

from kiseki.domain.photo.observation import PhotoObservation
from kiseki.domain.services.detectors.shared import (
    Located,
    StopExtraction,
    assemble,
    located_and_unlocated,
)
from kiseki.domain.shared.settings import StopSettings

NAME = "dbscan"
SPATIOTEMPORAL_NAME = "stdbscan"

UNVISITED = -2
NOISE = -1


def _neighbours(
    located: Sequence[Located], index: int, settings: StopSettings, in_time: bool
) -> list[int]:
    here = located[index]
    found = []
    for other, item in enumerate(located):
        if here.location.distance_to(item.location) > settings.stay_radius:
            continue
        if in_time and abs(item.captured_at - here.captured_at) > settings.max_gap:
            continue
        found.append(other)
    return found


def _cluster(
    located: Sequence[Located], settings: StopSettings, in_time: bool
) -> list[list[Located]]:
    """DBSCAN proper. Labels are indices into `located`."""
    labels = [UNVISITED] * len(located)
    cluster = 0
    for index in range(len(located)):
        if labels[index] != UNVISITED:
            continue
        found = _neighbours(located, index, settings, in_time)
        if len(found) < settings.min_photographs:
            labels[index] = NOISE
            continue
        labels[index] = cluster
        queue = [other for other in found if other != index]
        while queue:
            other = queue.pop()
            if labels[other] == NOISE:
                labels[other] = cluster  # a border point, reachable but not core
            if labels[other] != UNVISITED:
                continue
            labels[other] = cluster
            reachable = _neighbours(located, other, settings, in_time)
            if len(reachable) >= settings.min_photographs:
                queue.extend(reachable)
        cluster += 1

    groups: list[list[Located]] = [[] for _ in range(cluster)]
    stray: list[list[Located]] = []
    for index, label in enumerate(labels):
        if label < 0:
            stray.append([located[index]])
        else:
            groups[label].append(located[index])
    return [group for group in groups if group] + stray


def _split_by_silence(group: Sequence[Located], settings: StopSettings) -> list[list[Located]]:
    """One place, cut into the visits it was actually made of."""
    ordered = sorted(group, key=lambda item: item.captured_at)
    visits: list[list[Located]] = [[ordered[0]]]
    for previous, item in pairwise(ordered):
        if item.captured_at - previous.captured_at > settings.max_gap:
            visits.append([])
        visits[-1].append(item)
    return visits


def detect(located: Sequence[Located], settings: StopSettings) -> list[list[Located]]:
    if not located:
        return []
    groups = []
    for cluster in _cluster(located, settings, in_time=False):
        groups.extend(_split_by_silence(cluster, settings))
    return groups


def detect_spatiotemporal(
    located: Sequence[Located], settings: StopSettings
) -> list[list[Located]]:
    """Time is already in the neighbour test, so nothing is split after."""
    if not located:
        return []
    return _cluster(located, settings, in_time=True)


def extract(observations: Sequence[PhotoObservation], settings: StopSettings) -> StopExtraction:
    located, unlocated = located_and_unlocated(observations)
    stops, in_transit = assemble(detect(located, settings), settings)
    return StopExtraction(stops, in_transit, unlocated)


def extract_spatiotemporal(
    observations: Sequence[PhotoObservation], settings: StopSettings
) -> StopExtraction:
    located, unlocated = located_and_unlocated(observations)
    stops, in_transit = assemble(detect_spatiotemporal(located, settings), settings)
    return StopExtraction(stops, in_transit, unlocated)
