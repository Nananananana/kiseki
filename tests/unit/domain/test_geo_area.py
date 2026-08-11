"""Specification for GeoArea."""

import pytest
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint

CENTRE = GeoPoint(35.0094, 135.6669)


class TestGeoArea:
    def test_contains_its_own_centre(self) -> None:
        assert GeoArea(CENTRE, Distance(100)).contains(CENTRE)

    def test_contains_a_nearby_point(self) -> None:
        nearby = GeoPoint(CENTRE.latitude + 0.0005, CENTRE.longitude)
        assert GeoArea(CENTRE, Distance(100)).contains(nearby)

    def test_excludes_a_distant_point(self) -> None:
        far = GeoPoint(CENTRE.latitude + 0.05, CENTRE.longitude)
        assert not GeoArea(CENTRE, Distance(100)).contains(far)

    def test_the_boundary_is_inclusive(self) -> None:
        edge = GeoPoint(CENTRE.latitude + 0.001, CENTRE.longitude)
        radius = CENTRE.distance_to(edge)
        assert GeoArea(CENTRE, radius).contains(edge)

    def test_rejects_a_non_positive_radius(self) -> None:
        with pytest.raises(ValueError, match="radius"):
            GeoArea(CENTRE, Distance(0))
