"""Specification for Speed."""

from datetime import timedelta

import pytest

from kiseki.domain.shared.geo import Distance
from kiseki.domain.shared.speed import Speed


class TestConversion:
    def test_converts_to_kilometers_per_hour(self) -> None:
        assert Speed(10).kilometers_per_hour == pytest.approx(36)

    def test_can_be_built_from_kilometers_per_hour(self) -> None:
        assert Speed.from_kilometers_per_hour(36).meters_per_second == pytest.approx(10)

    def test_round_trips(self) -> None:
        assert Speed.from_kilometers_per_hour(4.5).kilometers_per_hour == pytest.approx(4.5)


class TestDerivation:
    def test_derives_speed_from_a_distance_and_a_duration(self) -> None:
        derived = Speed.between(Distance(3600), timedelta(hours=1))
        assert derived.kilometers_per_hour == pytest.approx(3.6)

    def test_a_stationary_pair_of_photos_yields_zero(self) -> None:
        assert Speed.between(Distance(0), timedelta(minutes=5)) == Speed(0)

    def test_rejects_a_zero_duration(self) -> None:
        """Two photos with the same timestamp cannot imply a speed."""
        with pytest.raises(ValueError, match="positive"):
            Speed.between(Distance(100), timedelta(0))

    def test_rejects_a_negative_duration(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            Speed.between(Distance(100), timedelta(seconds=-1))


class TestConstraints:
    def test_rejects_a_negative_speed(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            Speed(-1)

    def test_rejects_a_non_finite_speed(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            Speed(float("inf"))

    def test_is_ordered_so_it_can_be_compared_to_a_threshold(self) -> None:
        walking = Speed.from_kilometers_per_hour(4.0)
        threshold = Speed.from_kilometers_per_hour(1.5)
        assert threshold < walking
