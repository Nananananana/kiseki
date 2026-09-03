"""The scikit-learn backed detectors.

Imported only once the extra is known to be present, so that importing
`kiseki` never reaches scikit-learn.

Everything here works in **radians on the haversine metric**, which is
the only way to cluster coordinates without lying about distance. A
Euclidean metric on latitude and longitude treats a degree of
longitude as a degree of latitude, and at this library's default
latitude that is an 18% error before anything else happens -- the kind
of mistake that produces plausible clusters nobody can fault.

`stay_radius` therefore becomes `radius / EARTH_RADIUS` in radians,
and the same number means the same distance everywhere on Earth.
"""

from collections.abc import Sequence
from typing import Any

from kiseki.domain.photo.observation import PhotoObservation
from kiseki.domain.services.detectors.density import _split_by_silence
from kiseki.domain.services.detectors.shared import (
    Located,
    StopExtraction,
    assemble,
    located_and_unlocated,
)
from kiseki.domain.shared.geo import EARTH_RADIUS_METERS
from kiseki.domain.shared.settings import StopSettings

HAVERSINE = "haversine"


def _radians(located: Sequence[Located]) -> Any:
    import numpy

    return numpy.radians([[item.location.latitude, item.location.longitude] for item in located])


def _labels(kind: str, points: Any, settings: StopSettings) -> Any:
    from sklearn.cluster import DBSCAN, HDBSCAN, OPTICS

    eps = settings.stay_radius.meters / EARTH_RADIUS_METERS

    if kind == "dbscan-indexed":
        # ball_tree is the whole point: the same algorithm as the pure
        # detector, with the neighbour search done by an index.
        model = DBSCAN(
            eps=eps,
            min_samples=settings.min_photographs,
            metric=HAVERSINE,
            algorithm="ball_tree",
        )
    elif kind == "hdbscan":
        # No eps at all. The only question asked is how small a place
        # may be, which is the parameter this library already has a
        # measured number for.
        model = HDBSCAN(
            min_cluster_size=max(2, settings.min_photographs),
            metric=HAVERSINE,
            copy=True,  # named rather than defaulted: 1.10 changes it
        )
    elif kind == "optics":
        # max_eps is a ceiling rather than a rule: OPTICS finds the
        # radius each cluster actually needs, below this one.
        model = OPTICS(
            min_samples=settings.min_photographs,
            max_eps=eps,
            metric=HAVERSINE,
        )
    else:  # pragma: no cover - the registry never offers another name
        raise ValueError(f"{kind!r} is not a scikit-learn detector")

    return model.fit(points).labels_


def extract_with(
    kind: str, observations: Sequence[PhotoObservation], settings: StopSettings
) -> StopExtraction:
    located, unlocated = located_and_unlocated(observations)
    if not located:
        return StopExtraction((), (), unlocated)

    labels = _labels(kind, _radians(located), settings)

    places: dict[int, list[Located]] = {}
    stray: list[list[Located]] = []
    for item, label in zip(located, labels, strict=True):
        if int(label) < 0:
            stray.append([item])
        else:
            places.setdefault(int(label), []).append(item)

    # A spatial cluster is a place, not a visit: every photograph ever
    # taken at home is one cluster spanning years. Cut each into the
    # visits it was made of, by the same silence that ends a stay
    # everywhere else.
    groups: list[list[Located]] = []
    for place in places.values():
        groups.extend(_split_by_silence(place, settings))
    groups.extend(stray)

    stops, in_transit = assemble(groups, settings)
    return StopExtraction(stops, in_transit, unlocated)
