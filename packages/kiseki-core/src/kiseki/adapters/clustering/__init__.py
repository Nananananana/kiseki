"""Detectors that need a library, and the seam that makes them optional.

`kiseki.domain.services.detectors` holds four detectors written in
plain Python, because the domain may not depend on anything and
because a reference implementation you can read is worth having. What
it cannot hold is a spatial index or an algorithm nobody sensible
reimplements, and those are the two things that decide whether this
library can answer what its neighbours answer.

So they live here. The adapters layer is where a dependency belongs,
`kiseki` still declares **no unconditional dependency** -- checked
against a built wheel's `Requires-Dist` -- and the machinery arrives
under an extra:

    uv pip install "kiseki[clustering]"

Without it, everything in the domain works and the names below are
absent from the choices, with a message saying what to install rather
than a stack trace about scikit-learn.

## What the extra buys, and it is two different things

**Speed.** The pure-Python `dbscan` compares every photograph with
every other, because an index is a dependency. `dbscan-indexed` uses a
ball tree on the haversine metric, which is the same algorithm and the
same answers with the neighbour search done properly.

**Reach.** `hdbscan` and `optics` do something the other four cannot:
they find clusters of **varying density**. Every detector above them
takes one radius and applies it everywhere, so a dense city centre and
a sparse hillside cannot both be right. HDBSCAN asks for no radius at
all -- only how small a place may be -- and OPTICS asks for one as a
ceiling rather than a rule.

That matters here more than it looks. `stay_radius` defaults to 300
metres because that was measured against one library (ADR-0006). A
reader whose life happens at two scales has never had a good answer
from a single radius, and neither has any of the four pure detectors.

## Licences

scikit-learn is BSD-3-Clause and NumPy is BSD-3-Clause; both are usable
in commercial work, which is why these two and not something stronger.
"""

from collections.abc import Sequence
from importlib.util import find_spec

from kiseki.domain.photo.observation import PhotoObservation
from kiseki.domain.services.detectors import DETECTORS, StopDetector, StopExtraction
from kiseki.domain.shared.settings import StopSettings

EXTRA = "clustering"
REQUIRES = ("sklearn", "numpy")

ACCELERATED = ("dbscan-indexed", "hdbscan", "optics")
"""Named here rather than discovered, so the list a reader is offered
is the same list whether or not the extra is installed. A registry
that shrinks silently when an import fails cannot tell a reader the
difference between *not available* and *does not exist*."""


def is_available() -> bool:
    """Whether the extra is installed. Asked without importing it, so
    that a library which is present but broken still fails loudly at
    the point of use rather than being reported absent here."""
    return all(find_spec(name) is not None for name in REQUIRES)


def missing_extra(name: str) -> str:
    return (
        f"{name!r} needs the '{EXTRA}' extra, which is not installed. "
        f'Install it with `pip install "kiseki[{EXTRA}]"`, or choose one of the '
        f"detectors that need nothing: {', '.join(DETECTORS)}."
    )


def _adapter(kind: str) -> StopDetector:
    def extract(observations: Sequence[PhotoObservation], settings: StopSettings) -> StopExtraction:
        if not is_available():
            raise ValueError(missing_extra(kind))
        from kiseki.adapters.clustering.scikit import extract_with

        return extract_with(kind, observations, settings)

    return extract


def available_detectors() -> dict[str, StopDetector]:
    """Every detector this installation can actually run.

    The pure ones always; the accelerated ones only when the extra is
    there. Callers that want the full list of names, installed or not,
    read `ACCELERATED` -- the two questions are different and the
    answers are given separately on purpose.
    """
    detectors = dict(DETECTORS)
    if is_available():
        detectors.update({name: _adapter(name) for name in ACCELERATED})
    return detectors


def every_name() -> tuple[str, ...]:
    """Every name that exists, whether or not it can run here."""
    return tuple(DETECTORS) + ACCELERATED


def detector_named(name: str) -> StopDetector:
    """Resolve a name across both registries.

    The domain has a resolver of its own and it stays -- the domain
    may not know that this layer exists. This one is what a caller
    with the whole picture uses, and the difference shows in the
    refusal: an accelerated name that is real but not installed is
    told what to install, and only a name that is not a detector at
    all is told the list.
    """
    detectors = available_detectors()
    if name in detectors:
        return detectors[name]
    if name in ACCELERATED:
        raise ValueError(missing_extra(name))
    raise ValueError(f"{name!r} is not a stop detector. Choose one of: {', '.join(every_name())}")
