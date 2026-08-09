"""Specification for PhotoId and PhotoObservation."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint

JST = timezone(timedelta(hours=9))
MOMENT = datetime(2025, 5, 3, 10, 24, 31, tzinfo=JST)
KYOTO = GeoPoint(35.0094, 135.6669)


class TestPhotoId:
    def test_carries_its_value(self) -> None:
        assert PhotoId("sha256:abc").value == "sha256:abc"

    def test_rejects_an_empty_value(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            PhotoId("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            PhotoId("   ")

    def test_is_hashable_so_it_can_key_a_lookup(self) -> None:
        assert len({PhotoId("a"), PhotoId("a"), PhotoId("b")}) == 2

    def test_is_immutable(self) -> None:
        identifier = PhotoId("a")
        with pytest.raises(FrozenInstanceError):
            identifier.value = "b"  # type: ignore[misc]


class TestPhotoObservation:
    def test_holds_a_time_and_an_optional_place(self) -> None:
        observation = PhotoObservation(PhotoId("a"), MOMENT, KYOTO)
        assert observation.location == KYOTO

    def test_a_location_is_optional(self) -> None:
        """A large share of real photographs carry no coordinates."""
        assert PhotoObservation(PhotoId("a"), MOMENT).location is None

    def test_rejects_a_naive_timestamp(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            PhotoObservation(PhotoId("a"), datetime(2025, 5, 3, 10, 24, 31))

    def test_reports_whether_it_is_located(self) -> None:
        assert PhotoObservation(PhotoId("a"), MOMENT, KYOTO).is_located
        assert not PhotoObservation(PhotoId("a"), MOMENT).is_located
