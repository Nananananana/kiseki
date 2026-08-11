"""Specification for the thresholds that govern outing assembly."""

from datetime import timedelta

import pytest
from kiseki.domain.shared.settings import OutingSettings


class TestDefaults:
    def test_are_usable_without_any_argument(self) -> None:
        assert OutingSettings().max_absence > timedelta(0)

    def test_are_documented_values_rather_than_magic_numbers(self) -> None:
        assert OutingSettings().max_absence == timedelta(hours=8)


class TestConstraints:
    def test_rejects_a_non_positive_tolerance(self) -> None:
        with pytest.raises(ValueError, match="max_absence"):
            OutingSettings(max_absence=timedelta(0))

    def test_is_immutable(self) -> None:
        from dataclasses import FrozenInstanceError

        settings = OutingSettings()
        with pytest.raises(FrozenInstanceError):
            settings.max_absence = timedelta(hours=1)  # type: ignore[misc]
