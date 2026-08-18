"""Timelines may be laid beside each other; they may not be blamed."""

from datetime import UTC, datetime

import pytest
from kiseki.domain.services.cross_timeline import (
    MIN_MONTHS,
    Drift,
    DriftStage,
    Relation,
    TimelineComparison,
    compare_timelines,
    derive_drift,
    monthly_counts,
)


def _moments(*months: tuple[int, int, int]) -> list[datetime]:
    made: list[datetime] = []
    for year, month, count in months:
        for day in range(count):
            made.append(datetime(year, month, 1 + day, 12, tzinfo=UTC))
    return made


def test_months_without_events_are_counted_as_none() -> None:
    counts = monthly_counts(_moments((2026, 1, 2), (2026, 3, 1)))
    assert counts == {"2026-01": 2, "2026-02": 0, "2026-03": 1}


def test_no_moments_is_no_timeline() -> None:
    assert monthly_counts([]) == {}


def test_two_timelines_that_rise_together_are_said_to() -> None:
    left = {"2026-01": 1, "2026-02": 3, "2026-03": 5, "2026-04": 8}
    right = {"2026-01": 2, "2026-02": 5, "2026-03": 9, "2026-04": 14}
    result = compare_timelines(("photographs", left), ("outings", right))
    assert result.relation is Relation.CO_OCCURRING
    assert result.months == 4
    assert "not causing" in result.caution


def test_two_timelines_that_pull_apart_are_said_to() -> None:
    left = {"2026-01": 1, "2026-02": 3, "2026-03": 5, "2026-04": 8}
    right = {"2026-01": 9, "2026-02": 6, "2026-03": 4, "2026-04": 1}
    assert compare_timelines(("a", left), ("b", right)).relation is Relation.DIVERGENT


def test_a_short_history_says_it_cannot_say() -> None:
    left = {"2026-01": 1, "2026-02": 2}
    right = {"2026-01": 3, "2026-02": 1}
    result = compare_timelines(("a", left), ("b", right))
    assert result.relation is Relation.UNKNOWN
    assert result.alignment == 0.0


def test_a_flat_timeline_shares_no_movement() -> None:
    left = {f"2026-0{index}": 4 for index in range(1, 6)}
    right = {f"2026-0{index}": index for index in range(1, 6)}
    assert compare_timelines(("a", left), ("b", right)).relation is Relation.UNRELATED


def test_a_series_does_not_compare_with_itself() -> None:
    with pytest.raises(ValueError):
        TimelineComparison(left="a", right="a", months=5, relation=Relation.UNKNOWN, alignment=0.0)


def test_an_ordinary_month_is_baseline() -> None:
    counts = {"2026-01": 5, "2026-02": 6, "2026-03": 5, "2026-04": 6}
    drift = derive_drift("photographs", counts)
    assert drift is not None
    assert drift.stage is DriftStage.BASELINE


def test_a_change_that_holds_has_stopped_being_an_event() -> None:
    counts = {
        "2025-09": 5,
        "2025-10": 6,
        "2025-11": 5,
        "2025-12": 20,
        "2026-01": 21,
        "2026-02": 22,
    }
    drift = derive_drift("photographs", counts)
    assert drift is not None
    assert drift.stage is DriftStage.PERSISTENT


def test_one_month_unlike_the_rest_is_a_new_shape() -> None:
    counts = {
        "2025-09": 5,
        "2025-10": 6,
        "2025-11": 5,
        "2025-12": 6,
        "2026-01": 5,
        "2026-02": 40,
    }
    drift = derive_drift("photographs", counts)
    assert drift is not None
    assert drift.stage is DriftStage.NEW_PATTERN
    assert drift.latest == 40.0


def test_too_short_a_history_drifts_nowhere() -> None:
    assert derive_drift("photographs", {"2026-01": 1, "2026-02": 2}) is None
    assert MIN_MONTHS == 4


def test_a_drift_names_the_series_it_describes() -> None:
    with pytest.raises(ValueError):
        Drift(
            series="",
            months=5,
            stage=DriftStage.BASELINE,
            latest=1.0,
            baseline=1.0,
        )
