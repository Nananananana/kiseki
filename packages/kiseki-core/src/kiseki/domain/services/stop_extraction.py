"""Separating stays from journeys.

The only evidence available is when and where photographs were taken. A
stay shows up as a cluster in space that persists in time; a journey
shows up as photographs strung out along a line, taken faster than
anyone walks.

**How that is decided is now a choice**, and the choices live in
`kiseki.domain.services.detectors` with the argument for each. This
module is the seam: it keeps the signature every caller already uses,
and hands the work to whichever detector was named.

`extract_stops` without a detector is `sequential`, which is what this
library did before there was a choice and what its measured defaults
belong to (ADR-0006). Nothing about an existing library changes by
upgrading.
"""

from collections.abc import Sequence

from kiseki.domain.photo.observation import PhotoObservation
from kiseki.domain.services.detectors import (
    DEFAULT_DETECTOR,
    NAMES,
    StopDetector,
    detector_named,
)
from kiseki.domain.services.detectors.shared import StopExtraction
from kiseki.domain.shared.settings import StopSettings

__all__ = ["NAMES", "StopExtraction", "extract_stops"]


def extract_stops(
    observations: Sequence[PhotoObservation],
    settings: StopSettings | None = None,
    detector: StopDetector | str | None = None,
) -> StopExtraction:
    """Group photographs into stays.

    Photographs without coordinates are set aside rather than
    discarded; they can still be placed by time once outings are
    assembled.

    `detector` takes a name or a callable. A name is looked up, and an
    unknown one is refused with the alternatives listed rather than
    quietly falling back to the default -- a reader who mistyped an
    algorithm and got the default would be told their answers came
    from a detector they did not choose.
    """
    rules = settings if settings is not None else StopSettings()
    chosen = detector if detector is not None else DEFAULT_DETECTOR
    if isinstance(chosen, str):
        chosen = detector_named(chosen)
    return chosen(observations, rules)
