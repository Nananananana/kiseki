"""A day's worth of moving, counted and nothing more."""

from datetime import date

import pytest
from kiseki.domain.activity.daily import MAX_PLAUSIBLE_STEPS, DailyActivity

DAY = date(2026, 8, 19)


def test_a_day_is_a_count_and_a_date() -> None:
    activity = DailyActivity(day=DAY, steps=8421)
    assert activity.steps == 8421
    assert activity.distance_m is None
    assert activity.distance_km is None


def test_the_optional_parts_stay_optional() -> None:
    activity = DailyActivity(day=DAY, steps=8421, distance_m=6200.0, floors=12)
    assert activity.distance_km == 6.2
    assert activity.floors == 12


def test_a_negative_count_is_refused() -> None:
    with pytest.raises(ValueError):
        DailyActivity(day=DAY, steps=-1)


def test_an_impossible_day_is_refused() -> None:
    with pytest.raises(ValueError):
        DailyActivity(day=DAY, steps=MAX_PLAUSIBLE_STEPS + 1)


def test_an_unusual_day_is_not_argued_with() -> None:
    """Forty thousand steps is a long walk, not a fault."""
    assert DailyActivity(day=DAY, steps=40_000).steps == 40_000


def test_a_negative_distance_is_refused() -> None:
    with pytest.raises(ValueError):
        DailyActivity(day=DAY, steps=100, distance_m=-1.0)
