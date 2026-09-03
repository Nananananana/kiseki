"""Four ways to decide what counts as a stay, and one way to choose.

A stop detector takes photographs and returns stays, photographs in
transit, and photographs with no coordinates. What it does in between
is the whole disagreement:

| name | what it asks | from the literature |
|---|---|---|
| `sequential` | is this still the same stay | this library, ADR-0006 |
| `staypoint` | is this still within the radius of where the stay began | Li et al., ACM GIS 2008 |
| `dbscan` | where is this person densely present | Ester et al., KDD 1996 |
| `stdbscan` | the same, with a radius in time as well | Birant and Kut, DKE 2007 |

Every one is implemented here from its published description, in
plain Python. That is not stubbornness: `kiseki` declares **no
runtime dependency at all**, and a check against a built wheel keeps
it that way, so an implementation that arrived by adding scikit-learn
would arrive by breaking the one promise this package makes.

## Choosing is a decision, not a preference

Swapping the detector changes what the word *stop* means in every
answer above it -- how many outings there were, which places are
anchors, what `suggest` is overdue about. Two detectors on one library
are two libraries as far as a reader is concerned.

So the name is a setting like any other (`docs/algorithms.md`), the
default is the one whose numbers came from somebody's real
photographs, and `kiseki build` prints which one it used. A derivation
that cannot say which algorithm produced it is a derivation nobody can
argue with.

## Adding one

A detector is a module with `NAME` and `extract(observations,
settings)`. Add it to `DETECTORS` below. The list is written out
rather than discovered by walking the package, because a registry
built by a walk is a registry that quietly holds nothing on the day
the walk stops matching.
"""

from collections.abc import Sequence
from typing import Protocol

from kiseki.domain.photo.observation import PhotoObservation
from kiseki.domain.services.detectors import density, sequential, staypoint
from kiseki.domain.services.detectors.shared import Located, StopExtraction
from kiseki.domain.shared.settings import StopSettings


class StopDetector(Protocol):
    """What every detector is, from the outside."""

    def __call__(
        self, observations: Sequence[PhotoObservation], settings: StopSettings
    ) -> StopExtraction: ...


DETECTORS: dict[str, StopDetector] = {
    sequential.NAME: sequential.extract,
    staypoint.NAME: staypoint.extract,
    density.NAME: density.extract,
    density.SPATIOTEMPORAL_NAME: density.extract_spatiotemporal,
}

DEFAULT_DETECTOR = sequential.NAME
"""The only one whose thresholds were measured against a real photo
library (ADR-0006). The others are correct implementations of
published algorithms with this library's thresholds handed to them,
which is a different and weaker claim."""

NAMES = tuple(DETECTORS)


def detector_named(name: str) -> StopDetector:
    """The detector by name, or a refusal that lists the alternatives."""
    try:
        return DETECTORS[name]
    except KeyError:
        raise ValueError(
            f"{name!r} is not a stop detector. Choose one of: {', '.join(NAMES)}"
        ) from None


__all__ = [
    "DEFAULT_DETECTOR",
    "DETECTORS",
    "NAMES",
    "Located",
    "StopDetector",
    "StopExtraction",
    "detector_named",
]
