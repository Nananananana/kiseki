"""Specification for the thresholds that govern stop extraction."""

from datetime import timedelta

import pytest
from kiseki.domain.shared.geo import Distance
from kiseki.domain.shared.settings import StopSettings
from kiseki.domain.shared.speed import Speed


class TestDefaults:
    def test_are_usable_without_any_argument(self) -> None:
        settings = StopSettings()
        assert settings.stay_radius.meters > 0
        assert settings.max_gap > timedelta(0)

    def test_are_documented_values_rather_than_magic_numbers(self) -> None:
        settings = StopSettings()
        assert settings.stay_radius == Distance(300)
        assert settings.drift_speed == Speed.from_kilometers_per_hour(1.5)
        assert settings.max_gap == timedelta(minutes=90)
        assert settings.min_duration == timedelta(minutes=10)
        assert settings.min_photographs == 5


class TestConstraints:
    def test_rejects_a_non_positive_gap(self) -> None:
        with pytest.raises(ValueError, match="max_gap"):
            StopSettings(max_gap=timedelta(0))

    def test_rejects_a_negative_minimum_duration(self) -> None:
        with pytest.raises(ValueError, match="min_duration"):
            StopSettings(min_duration=timedelta(minutes=-1))

    def test_rejects_fewer_than_one_photograph(self) -> None:
        with pytest.raises(ValueError, match="min_photographs"):
            StopSettings(min_photographs=0)

    def test_is_immutable(self) -> None:
        from dataclasses import FrozenInstanceError

        settings = StopSettings()
        with pytest.raises(FrozenInstanceError):
            settings.min_photographs = 5  # type: ignore[misc]
