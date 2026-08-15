"""The screen reading run: read every screenshot once, resumably.

The store is the progress record; refusals are recorded and never
asked again; an unavailable model pauses the run. See ADR-0030.
"""

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


def _photo(identifier: str, kind: str, ref: str | None) -> PhotoObservation:
    return PhotoObservation(PhotoId(identifier), AT, None, thumbnail_ref=ref, content_kind=kind)


def _photos(*observations: PhotoObservation) -> InMemoryPhotoRepository:
    repository = InMemoryPhotoRepository()
    repository.save_all(list(observations))
    return repository


class TestScreenReadingRun:
    def test_reads_screenshots_and_nothing_else(self) -> None:
        photos = _photos(
            _photo("s1", "screenshot", "r1"),
            _photo("p1", "photo", "r2"),
            _photo("o1", "other", "r3"),
        )
        readings = FakeScreenshotReadingRepository()
        report = run_screen_reading(
            photos, readings, _Thumbs({"r1": b"img"}), FakeScreenshotReader()
        )
        assert report.read == 1
        assert readings.get(PhotoId("s1")) is not None
        assert readings.get(PhotoId("p1")) is None

    def test_a_screenshot_without_a_thumbnail_is_unreferenced(self) -> None:
        photos = _photos(_photo("s1", "screenshot", None))
        report = run_screen_reading(
            photos, FakeScreenshotReadingRepository(), _Thumbs({}), FakeScreenshotReader()
        )
        assert report.unreferenced == 1
        assert report.read == 0

    def test_a_missing_thumbnail_is_recorded_as_a_refusal(self) -> None:
        photos = _photos(_photo("s1", "screenshot", "gone"))
        readings = FakeScreenshotReadingRepository()
        report = run_screen_reading(photos, readings, _Thumbs({}), FakeScreenshotReader())
        assert report.refused == 1
        stored = readings.get(PhotoId("s1"))
        assert stored is not None and not stored.answered

    def test_what_is_read_is_never_read_again(self) -> None:
        photos = _photos(_photo("s1", "screenshot", "r1"))
        readings = FakeScreenshotReadingRepository()
        thumbs = _Thumbs({"r1": b"img"})
        run_screen_reading(photos, readings, thumbs, FakeScreenshotReader())
        report = run_screen_reading(photos, readings, thumbs, FakeScreenshotReader())
        assert report.already == 1
        assert report.read == 0

    def test_an_unavailable_model_pauses_the_run(self) -> None:
        photos = _photos(_photo("s1", "screenshot", "r1"), _photo("s2", "screenshot", "r2"))
        reader = FakeScreenshotReader(fail_on=lambda image: True)
        report = run_screen_reading(
            photos,
            FakeScreenshotReadingRepository(),
            _Thumbs({"r1": b"a", "r2": b"b"}),
            reader,
        )
        assert report.paused
        assert report.read == 0

    def test_the_limit_stops_the_run(self) -> None:
        photos = _photos(_photo("s1", "screenshot", "r1"), _photo("s2", "screenshot", "r2"))
        report = run_screen_reading(
            photos,
            FakeScreenshotReadingRepository(),
            _Thumbs({"r1": b"a", "r2": b"b"}),
            FakeScreenshotReader(),
            limit=1,
        )
        assert report.read == 1
