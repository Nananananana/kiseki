"""Shared contract for every ScreenshotReadingRepository implementation."""

from datetime import UTC, datetime

import pytest
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.ports.screens import ScreenshotReadingRepository

AT = datetime(2026, 6, 1, 12, tzinfo=UTC)


def build_reading(identifier: str = "p1", refused: str | None = None) -> ScreenshotReading:
    return ScreenshotReading(
        photo_id=PhotoId(identifier),
        category="product",
        labels=("camera",) if refused is None else (),
        model="m" if refused is None else "",
        created_at=AT,
        refused=refused,
    )


class ScreenshotReadingRepositoryContract:
    @pytest.fixture
    def readings(self) -> ScreenshotReadingRepository:
        raise NotImplementedError("override the 'readings' fixture")

    def test_starts_empty(self, readings: ScreenshotReadingRepository) -> None:
        assert readings.get(PhotoId("p1")) is None
        assert readings.all() == ()

    def test_a_reading_survives_storage(self, readings: ScreenshotReadingRepository) -> None:
        readings.save(build_reading())
        stored = readings.get(PhotoId("p1"))
        assert stored is not None
        assert stored.category == "product"
        assert stored.labels == ("camera",)
        assert stored.answered

    def test_a_refusal_survives_storage(self, readings: ScreenshotReadingRepository) -> None:
        readings.save(build_reading(refused="unparseable"))
        stored = readings.get(PhotoId("p1"))
        assert stored is not None
        assert not stored.answered
