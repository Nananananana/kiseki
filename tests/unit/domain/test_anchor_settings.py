"""Specification for the thresholds that govern anchor estimation."""

import pytest
from kiseki.domain.shared.geo import Distance
from kiseki.domain.shared.settings import AnchorSettings


class TestDefaults:
    def test_are_documented_values_rather_than_magic_numbers(self) -> None:
        settings = AnchorSettings()
        assert settings.cluster_radius == Distance(500)
        assert settings.min_visits == 5
        assert settings.night_hours == (20, 6)
        assert settings.working_hours == (10, 17)

    def test_the_night_window_wraps_past_midnight(self) -> None:
        low, high = AnchorSettings().night_hours
        assert low > high


class TestConstraints:
    def test_rejects_a_visit_threshold_below_one(self) -> None:
        with pytest.raises(ValueError, match="min_visits"):
            AnchorSettings(min_visits=0)

    def test_is_immutable(self) -> None:
        from dataclasses import FrozenInstanceError

        settings = AnchorSettings()
        with pytest.raises(FrozenInstanceError):
            settings.min_visits = 10  # type: ignore[misc]
