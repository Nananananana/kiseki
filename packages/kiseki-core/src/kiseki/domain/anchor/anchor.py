"""A place photographed on enough separate days to be part of a person's life."""

from dataclasses import dataclass

from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import GeoArea
from kiseki.domain.shared.time_range import TimeRange


@dataclass(frozen=True)
class Anchor:
    """Somewhere returned to, described by what was observed rather than named.

    No attempt is made to say whether this is a home, a workplace, or a family
    house. Those categories depend on how a person lives, and the shares below
    carry more than a label would: a place with a night share of 1.0 and a
    daytime share of 0.0 needs no name for a reader to understand it.
    """

    area: GeoArea
    period: TimeRange
    visit_days: int
    night_days: int
    weekday_days: int
    daytime_days: int
    photograph_count: int
    confidence: Confidence

    def __post_init__(self) -> None:
        if self.visit_days < 1:
            raise ValueError("an anchor needs at least one visit")
        for label, value in (
            ("night_days", self.night_days),
            ("weekday_days", self.weekday_days),
            ("daytime_days", self.daytime_days),
        ):
            if value < 0:
                raise ValueError(f"{label} cannot be negative")
            if value > self.visit_days:
                raise ValueError(f"{label} cannot exceed visit_days")

    @property
    def night_share(self) -> float:
        """Days including a photograph at night, as a share of all visits."""
        return self.night_days / self.visit_days

    @property
    def weekday_share(self) -> float:
        return self.weekday_days / self.visit_days

    @property
    def daytime_share(self) -> float:
        return self.daytime_days / self.visit_days

    @property
    def photographs_per_visit(self) -> float:
        return self.photograph_count / self.visit_days
