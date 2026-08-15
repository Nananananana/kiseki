"""Stay captioning honours consent: withheld photographs never enter
the representative selection (ADR-0035, completing ADR-0032)."""

from datetime import UTC, datetime, timedelta

from kiseki.adapters.fake.captions import FakeCaptionRepository
from kiseki.adapters.fake.models import FakeImageCaptioner
from kiseki.adapters.fake.thumbnails import FakeThumbnailSource
from kiseki.application.captioning import CaptionRunReport, run_captioning
from kiseki.domain.caption.caption import CaptionKey
from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange

START = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)


def _photo(
    pid: str, minutes: int = 0, thumb: str | None = None, preference: bool | None = None
) -> PhotoObservation:
    return PhotoObservation(
        PhotoId(pid),
        START + timedelta(minutes=minutes),
        None,
        thumbnail_ref=thumb,
        content_kind="photo",
        use_for_preference=preference,
    )


def _outing(*pids: str) -> Outing:
    span = TimeRange(START, START + timedelta(minutes=30))
    stop = Stop(tuple(PhotoId(pid) for pid in pids), span, GeoPoint(35.0, 139.0))
    return Outing.of([stop])


class StubPhotos:
    def __init__(self, observations: list[PhotoObservation]) -> None:
        self._observations = tuple(observations)

    def all(self) -> tuple[PhotoObservation, ...]:
        return self._observations


class StubOutings:
    def __init__(self, outings: list[Outing]) -> None:
        self._outings = tuple(outings)

    def all(self) -> tuple[Outing, ...]:
        return self._outings


class TestCaptionConsent:
    def test_a_withheld_photograph_leaves_the_selection(self) -> None:
        photos = [
            _photo("sha256:aa", 0, thumb="t/aa"),
            _photo("sha256:bb", 1, thumb="t/bb", preference=False),
        ]
        captioner = FakeImageCaptioner()
        captions = FakeCaptionRepository()
        report = run_captioning(
            outings=StubOutings([_outing("sha256:aa", "sha256:bb")]),
            photos=StubPhotos(photos),
            captions=captions,
            thumbnails=FakeThumbnailSource({"t/aa": b"aa", "t/bb": b"bb"}),
            captioner=captioner,
        )
        assert report.captioned == 1
        assert report.withheld == 0
        assert captioner.seen[0].images == (b"aa",)
        assert captions.get(CaptionKey.of([PhotoId("sha256:aa")])) is not None

    def test_a_stay_of_only_withheld_photographs_is_counted(self) -> None:
        captioner = FakeImageCaptioner()
        report = run_captioning(
            outings=StubOutings([_outing("sha256:aa")]),
            photos=StubPhotos([_photo("sha256:aa", 0, thumb="t/aa", preference=False)]),
            captions=FakeCaptionRepository(),
            thumbnails=FakeThumbnailSource({"t/aa": b"aa"}),
            captioner=captioner,
        )
        assert report.withheld == 1
        assert report.unreferenced == 0
        assert report.captioned == 0
        assert captioner.seen == []

    def test_a_stay_without_thumbnails_stays_unreferenced(self) -> None:
        report = run_captioning(
            outings=StubOutings([_outing("sha256:aa")]),
            photos=StubPhotos([_photo("sha256:aa", 0)]),
            captions=FakeCaptionRepository(),
            thumbnails=FakeThumbnailSource({}),
            captioner=FakeImageCaptioner(),
        )
        assert report.unreferenced == 1
        assert report.withheld == 0

    def test_legacy_photographs_still_take_part(self) -> None:
        report = run_captioning(
            outings=StubOutings([_outing("sha256:aa")]),
            photos=StubPhotos([_photo("sha256:aa", 0, thumb="t/aa", preference=None)]),
            captions=FakeCaptionRepository(),
            thumbnails=FakeThumbnailSource({"t/aa": b"aa"}),
            captioner=FakeImageCaptioner(),
        )
        assert report.captioned == 1
        assert report.withheld == 0

    def test_the_report_defaults_to_no_withheld(self) -> None:
        assert CaptionRunReport(1, 2, 3, 4, False).withheld == 0
