"""The screen run honours a withheld preference."""

from datetime import UTC, datetime

from kiseki.adapters.fake.screens import (
    FakeScreenshotReader,
    FakeScreenshotReadingRepository,
)
from kiseki.adapters.memory.repositories import InMemoryPhotoRepository
from kiseki.application.screen_reading import run_screen_reading
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.ports.thumbnails import ThumbnailMissingError

AT = datetime(2026, 6, 1, 12, tzinfo=UTC)


class _Thumbs:
    def __init__(self, known: dict[str, bytes]) -> None:
        self._known = known

    def read(self, thumbnail_ref: str) -> bytes:
        if thumbnail_ref not in self._known:
            raise ThumbnailMissingError(thumbnail_ref)
        return self._known[thumbnail_ref]


class TestScreenRunConsent:
    def test_a_withheld_screenshot_is_never_read(self) -> None:
        photos = InMemoryPhotoRepository()
        photos.save_all(
            [
                PhotoObservation(
                    PhotoId("s1"),
                    AT,
                    None,
                    thumbnail_ref="r1",
                    content_kind="screenshot",
                    use_for_preference=False,
                )
            ]
        )
        readings = FakeScreenshotReadingRepository()
        report = run_screen_reading(
            photos, readings, _Thumbs({"r1": b"img"}), FakeScreenshotReader()
        )
        assert report.withheld == 1
        assert report.read == 0
        assert readings.get(PhotoId("s1")) is None
