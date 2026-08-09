"""Specification for Confidence."""

import pytest

from kiseki.domain.shared.confidence import Confidence


class TestConstruction:
    def test_accepts_the_boundary_values(self) -> None:
        assert Confidence(0.0, 0).value == 0.0
        assert Confidence(1.0, 10).value == 1.0

    @pytest.mark.parametrize("value", [1.1, -0.1])
    def test_rejects_a_value_outside_the_unit_interval(self, value: float) -> None:
        with pytest.raises(ValueError, match="outside"):
            Confidence(value, 1)

    def test_rejects_a_non_finite_value(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            Confidence(float("nan"), 1)

    def test_rejects_a_negative_sample_size(self) -> None:
        with pytest.raises(ValueError, match="sample"):
            Confidence(0.5, -1)


class TestSupport:
    def test_unknown_carries_no_samples(self) -> None:
        assert Confidence.unknown() == Confidence(0.0, 0)

    def test_enough_samples_is_supported(self) -> None:
        assert Confidence(0.8, 12).is_supported_by(10)

    def test_a_high_value_on_few_samples_is_not_supported(self) -> None:
        """Certainty derived from three outings is not certainty."""
        assert not Confidence(0.9, 3).is_supported_by(10)
