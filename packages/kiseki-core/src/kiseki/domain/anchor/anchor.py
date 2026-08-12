"""A place returned to repeatedly."""

from dataclasses import dataclass
from enum import Enum

from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import GeoArea
from kiseki.domain.shared.time_range import TimeRange


class AnchorKind(Enum):
    """What sort of place this is, judged by when it is visited."""

    PRIMARY = "primary"
    """Where the person lives. The place they sleep most often."""

    WORKPLACE = "workplace"
    """Visited on weekdays, during the day, and never slept at."""

    SECONDARY = "secondary"
    """Another base: a family home, a partner's flat, a holiday place."""


@dataclass(frozen=True)
class Anchor:
    """A place, a period during which it was an anchor, and the evidence.

    Anchors carry a period rather than being timeless, because people move. A
    home from 2023 is still a fact about 2023 after the person has left it.
    """

    kind: AnchorKind
    area: GeoArea
    period: TimeRange
    visit_count: int
    night_count: int
    confidence: Confidence

    def __post_init__(self) -> None:
        if self.visit_count < 1:
            raise ValueError("an anchor needs at least one visit")
        if self.night_count < 0:
            raise ValueError("night count cannot be negative")

    @property
    def is_residential(self) -> bool:
        """Whether this is somewhere the person sleeps."""
        return self.kind in (AnchorKind.PRIMARY, AnchorKind.SECONDARY)
