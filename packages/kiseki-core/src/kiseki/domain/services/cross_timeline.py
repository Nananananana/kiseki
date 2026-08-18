"""Several timelines on one axis, and what may be said about them.

The library measures more than one thing over time: photographs taken,
outings made, screens read. Put two of them side by side and the eye
finds a story immediately -- and the story it finds is usually causal
and usually unearned. So this module can express co-occurrence and
nothing stronger. There is no word here for "because", and adding one
would be a change to the vocabulary rather than a change to the code.

Drift is described in four stages and never judged. A pattern that
became something else is not worse than the one before it; the
library says what changed and stops. See ADR-0058.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique
from statistics import mean, pstdev

MIN_MONTHS = 4
"""Fewer months than this and nothing can be said about a shape."""

ALIGNMENT_STRONG = 0.6
"""How closely two series must move together before their movement is
worth mentioning at all. Not a significance test -- a threshold for
saying "these moved together", which is all that is ever claimed."""

DRIFT_SIGMA = 1.5
"""How far from its own history a month must sit to count as a change
rather than as the ordinary variation of a life."""

PERSISTENT_MONTHS = 3
"""A change that holds this long has stopped being an event. The
months in this window are held out of the baseline: measuring a change
against a history that already contains it is how a change hides."""


@unique
class Relation(Enum):
    """Everything this library is willing to say about two timelines."""

    CO_OCCURRING = "moved together"
    DIVERGENT = "moved apart"
    UNRELATED = "no shared movement"
    UNKNOWN = "not enough history to say"


@unique
class DriftStage(Enum):
    """Where a timeline stands against its own past. Never a verdict."""

    BASELINE = "steady against its own history"
    GRADUAL = "drifting"
    PERSISTENT = "changed and stayed changed"
    NEW_PATTERN = "a shape its history does not contain"


@dataclass(frozen=True)
class TimelineComparison:
    """Two named series, what they did, and what may not be concluded."""

    left: str
    right: str
    months: int
    relation: Relation
    alignment: float
    caution: str = "moving together is not causing: nothing here says one made the other happen"

    def __post_init__(self) -> None:
        if not self.left or not self.right:
            raise ValueError("a comparison needs both series named")
        if self.left == self.right:
            raise ValueError("a series does not compare with itself")
        if not -1.0 <= self.alignment <= 1.0:
            raise ValueError("alignment lies within [-1, 1]")


@dataclass(frozen=True)
class Drift:
    """One series against its own history."""

    series: str
    months: int
    stage: DriftStage
    latest: float
    baseline: float

    def __post_init__(self) -> None:
        if not self.series:
            raise ValueError("a drift needs the series it describes")


def monthly_counts(moments: Sequence[datetime]) -> dict[str, int]:
    """Events per calendar month, months with none included as zero."""
    if not moments:
        return {}
    stamps = sorted(moment.replace(tzinfo=None) for moment in moments)
    counts: dict[str, int] = {}
    year, month = stamps[0].year, stamps[0].month
    last = stamps[-1]
    while (year, month) <= (last.year, last.month):
        counts[f"{year:04d}-{month:02d}"] = 0
        month += 1
        if month > 12:
            year, month = year + 1, 1
    for stamp in stamps:
        counts[f"{stamp.year:04d}-{stamp.month:02d}"] += 1
    return counts


def _aligned(left: Sequence[float], right: Sequence[float]) -> float:
    """Correlation over the shared months, zero when either never moves."""
    if len(left) < MIN_MONTHS:
        return 0.0
    left_mean, right_mean = mean(left), mean(right)
    left_spread, right_spread = pstdev(left), pstdev(right)
    if left_spread == 0 or right_spread == 0:
        return 0.0
    products = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right, strict=True))
    return products / (len(left) * left_spread * right_spread)


def compare_timelines(
    left: tuple[str, Mapping[str, int]],
    right: tuple[str, Mapping[str, int]],
) -> TimelineComparison:
    """What two timelines did over the months they share."""
    left_name, left_counts = left
    right_name, right_counts = right
    shared = sorted(set(left_counts) & set(right_counts))
    if len(shared) < MIN_MONTHS:
        return TimelineComparison(
            left=left_name,
            right=right_name,
            months=len(shared),
            relation=Relation.UNKNOWN,
            alignment=0.0,
        )
    alignment = _aligned(
        [float(left_counts[month]) for month in shared],
        [float(right_counts[month]) for month in shared],
    )
    if alignment >= ALIGNMENT_STRONG:
        relation = Relation.CO_OCCURRING
    elif alignment <= -ALIGNMENT_STRONG:
        relation = Relation.DIVERGENT
    else:
        relation = Relation.UNRELATED
    return TimelineComparison(
        left=left_name,
        right=right_name,
        months=len(shared),
        relation=relation,
        alignment=alignment,
    )


def derive_drift(series: str, counts: Mapping[str, int]) -> Drift | None:
    """Where a timeline stands against its own past, or None if too short."""
    months = sorted(counts)
    if len(months) < MIN_MONTHS:
        return None
    values = [float(counts[month]) for month in months]
    window = min(PERSISTENT_MONTHS, len(values) // 2)
    recent = values[-window:]
    history = values[:-window]
    latest = values[-1]
    baseline = mean(history)
    spread = pstdev(history)

    if spread == 0:
        stage = DriftStage.BASELINE if latest == baseline else DriftStage.NEW_PATTERN
    elif abs(latest - baseline) < DRIFT_SIGMA * spread:
        stage = DriftStage.BASELINE
    elif all(abs(value - baseline) >= DRIFT_SIGMA * spread for value in recent):
        stage = DriftStage.PERSISTENT
    elif abs(latest - baseline) >= 2 * DRIFT_SIGMA * spread:
        stage = DriftStage.NEW_PATTERN
    else:
        stage = DriftStage.GRADUAL
    return Drift(
        series=series,
        months=len(months),
        stage=stage,
        latest=latest,
        baseline=baseline,
    )
