"""Specification for GeoPoint and Distance."""

import math
from dataclasses import FrozenInstanceError

import pytest

from kiseki.domain.shared.geo import EARTH_RADIUS_METERS, Distance, GeoPoint

ONE_DEGREE_METERS = math.pi / 180 * EARTH_RADIUS_METERS


class TestDistance:
    def test_exposes_kilometers(self) -> None:
        assert Distance(2500).kilometers == 2.5

    def test_can_be_built_from_kilometers(self) -> None:
        assert Distance.from_kilometers(1.5) == Distance(1500)

    def test_zero_is_allowed(self) -> None:
        assert Distance(0).meters == 0

    def test_rejects_a_negative_value(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            Distance(-1)

    def test_rejects_a_non_finite_value(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            Distance(float("nan"))

    def test_is_ordered(self) -> None:
        assert Distance(10) < Distance(20)
        assert max(Distance(10), Distance(20)) == Distance(20)

    def test_is_immutable(self) -> None:
        distance = Distance(10)
        with pytest.raises(FrozenInstanceError):
            distance.meters = 20  # type: ignore[misc]


class TestGeoPoint:
    def test_accepts_the_boundary_values(self) -> None:
        assert GeoPoint(90, 180).latitude == 90
        assert GeoPoint(-90, -180).longitude == -180

    @pytest.mark.parametrize("latitude", [90.1, -90.1])
    def test_rejects_latitude_outside_the_range(self, latitude: float) -> None:
        with pytest.raises(ValueError, match="latitude"):
            GeoPoint(latitude, 0)

    @pytest.mark.parametrize("longitude", [180.1, -180.1])
    def test_rejects_longitude_outside_the_range(self, longitude: float) -> None:
        with pytest.raises(ValueError, match="longitude"):
            GeoPoint(0, longitude)

    def test_rejects_swapped_coordinates(self) -> None:
        """A point near Kyoto is (35.0, 135.7). The other way round is not a place."""
        with pytest.raises(ValueError, match="latitude"):
            GeoPoint(135.7, 35.0)

    def test_rejects_non_finite_coordinates(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            GeoPoint(float("inf"), 0)

    def test_is_hashable_so_it_can_be_used_in_sets(self) -> None:
        assert len({GeoPoint(35.0, 135.0), GeoPoint(35.0, 135.0)}) == 1

    def test_is_immutable(self) -> None:
        point = GeoPoint(35.0, 135.0)
        with pytest.raises(FrozenInstanceError):
            point.latitude = 36.0  # type: ignore[misc]


class TestGeoPointDistance:
    def test_distance_to_itself_is_zero(self) -> None:
        point = GeoPoint(35.0094, 135.6669)
        assert point.distance_to(point) == Distance(0)

    def test_one_degree_of_latitude(self) -> None:
        measured = GeoPoint(0, 0).distance_to(GeoPoint(1, 0))
        assert measured.meters == pytest.approx(ONE_DEGREE_METERS, abs=1)

    def test_one_degree_of_longitude_at_the_equator(self) -> None:
        measured = GeoPoint(0, 0).distance_to(GeoPoint(0, 1))
        assert measured.meters == pytest.approx(ONE_DEGREE_METERS, abs=1)

    def test_longitude_converges_towards_the_poles(self) -> None:
        """At 60 degrees north a degree of longitude spans half the distance."""
        measured = GeoPoint(60, 0).distance_to(GeoPoint(60, 1))
        assert measured.meters == pytest.approx(ONE_DEGREE_METERS / 2, rel=0.001)

    def test_antipodal_points_are_half_the_circumference_apart(self) -> None:
        measured = GeoPoint(0, 0).distance_to(GeoPoint(0, 180))
        assert measured.meters == pytest.approx(math.pi * EARTH_RADIUS_METERS, rel=1e-6)

    def test_is_symmetric(self) -> None:
        first = GeoPoint(35.0094, 135.6669)
        second = GeoPoint(34.9857, 135.7595)
        assert first.distance_to(second).meters == pytest.approx(second.distance_to(first).meters)

    def test_crosses_the_antimeridian_by_the_short_way(self) -> None:
        """Two points either side of the date line are close, not a world apart."""
        measured = GeoPoint(0, 179.5).distance_to(GeoPoint(0, -179.5))
        assert measured.meters == pytest.approx(ONE_DEGREE_METERS, abs=1)
