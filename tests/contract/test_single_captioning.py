"""The single-photo captioning run: eligibility, resumability, refusals."""

from datetime import datetime, timedelta, timezone

from kiseki.adapters.fake.models import FakeImageCaptioner
from kiseki.adapters.fake.singles import FakeSingleCaptionRepository
from kiseki.adapters.fake.thumbnails import FakeThumbnailSource
from kiseki.application.single_captioning import run_single_captioning
from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange
from kiseki.ports.models import Completion, ModelRefusedError, Usage

START = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)


def _photo(pid, minutes=0, kind=None, thumb=None, preference=None):
    return PhotoObservation(
        PhotoId(pid),
        START + timedelta(minutes=minutes),
        None,
        thumbnail_ref=thumb,
        content_kind=kind,
        use_for_preference=preference,
    )


def _outing_holding(pid, minutes=0):
    span = TimeRange(
        START + timedelta(minutes=minutes), START + timedelta(minutes=minutes + 30)
    )
    stop = Stop((PhotoId(pid),), span, GeoPoint(35.0, 139.0))
    return Outing.of([stop])


class StubPhotos:
    def __init__(self, observations):
        self._observations = tuple(observations)

    def all(self):
        return self._observations


class StubOutings:
    def __init__(self, outings=()):
        self._outings = tuple(outings)

    def all(self):
        return self._outings


def _run(photos, outings=(), images=None, captioner=None, singles=None, **kwargs):
    kept = singles if singles is not None else FakeSingleCaptionRepository()
    report = run_single_captioning(
        photos=StubPhotos(photos),
        outings=StubOutings(outings),
        singles=kept,
        thumbnails=FakeThumbnailSource(images or {}),
        captioner=captioner if captioner is not None else FakeImageCaptioner(),
        **kwargs,
    )
    return report, kept


def test_a_lone_photograph_is_captioned():
    captioner = FakeImageCaptioner()
    report, singles = _run(
        [_photo("p1", thumb="t/p1")], images={"t/p1": b"one"}, captioner=captioner
    )
    assert report.captioned == 1
    saved = singles.get(PhotoId("p1"))
    assert saved is not None
    assert saved.answered
    assert len(captioner.seen) == 1
    assert len(captioner.seen[0].images) == 1
    assert "2026-05-01" in captioner.seen[0].context


def test_a_photograph_inside_a_stay_is_left_alone():
    captioner = FakeImageCaptioner()
    report, singles = _run(
        [_photo("p1", thumb="t/p1")],
        outings=[_outing_holding("p1")],
        images={"t/p1": b"one"},
        captioner=captioner,
    )
    assert report.captioned == 0
    assert captioner.seen == []


def test_screenshots_and_documents_are_not_asked_about():
    report, singles = _run(
        [
            _photo("s1", kind="screenshot", thumb="t/s1"),
            _photo("d1", 1, kind="document", thumb="t/d1"),
        ],
        images={"t/s1": b"s", "t/d1": b"d"},
    )
    assert report.captioned == 0
    assert report.unreferenced == 0


def test_a_saved_image_counts_as_a_single_photograph():
    report, singles = _run([_photo("o1", kind="other", thumb="t/o1")], images={"t/o1": b"o"})
    assert report.captioned == 1


def test_a_withheld_photograph_is_never_asked_about():
    captioner = FakeImageCaptioner()
    report, singles = _run(
        [_photo("p1", thumb="t/p1", preference=False)],
        images={"t/p1": b"one"},
        captioner=captioner,
    )
    assert report.captioned == 0
    assert report.unreferenced == 0
    assert captioner.seen == []


def test_a_photograph_without_thumbnail_is_counted():
    report, singles = _run([_photo("p1")])
    assert report.unreferenced == 1
    assert report.captioned == 0


def test_a_second_run_skips_finished_work():
    photos = [_photo("p1", thumb="t/p1")]
    images = {"t/p1": b"one"}
    singles = FakeSingleCaptionRepository()
    first, _ = _run(photos, images=images, singles=singles)
    second, _ = _run(photos, images=images, singles=singles)
    assert first.captioned == 1
    assert second.captioned == 0
    assert second.already_captioned == 1


def test_a_missing_thumbnail_is_recorded_as_a_refusal():
    report, singles = _run([_photo("p1", thumb="t/p1")], images={})
    assert report.refused == 1
    saved = singles.get(PhotoId("p1"))
    assert saved is not None
    assert not saved.answered


class _OneRefusal:
    def __init__(self):
        self.calls = 0

    def caption(self, requests):
        completions = []
        for _request in requests:
            self.calls += 1
            if self.calls == 1:
                raise ModelRefusedError("declined")
            completions.append(Completion(text="a scene", model="stub"))
        return completions

    @property
    def usage(self):
        return Usage()


def test_a_model_refusal_is_recorded_and_the_run_continues():
    report, singles = _run(
        [_photo("p1", thumb="t/p1"), _photo("p2", 1, thumb="t/p2")],
        images={"t/p1": b"one", "t/p2": b"two"},
        captioner=_OneRefusal(),
    )
    assert report.refused == 1
    assert report.captioned == 1
    refusal = singles.get(PhotoId("p1"))
    assert refusal is not None
    assert not refusal.answered


def test_an_unavailable_model_pauses_the_run():
    captioner = FakeImageCaptioner(fail_on=lambda request: True)
    report, singles = _run(
        [_photo("p1", thumb="t/p1"), _photo("p2", 1, thumb="t/p2")],
        images={"t/p1": b"one", "t/p2": b"two"},
        captioner=captioner,
    )
    assert report.paused
    assert report.captioned == 0
    assert len(captioner.seen) == 1


def test_a_paused_run_resumes_where_it_stopped():
    photos = [_photo("p1", thumb="t/p1"), _photo("p2", 1, thumb="t/p2")]
    images = {"t/p1": b"one", "t/p2": b"two"}
    singles = FakeSingleCaptionRepository()
    flaky = FakeImageCaptioner(fail_on=lambda request: request.images[0] == b"two")
    first, _ = _run(photos, images=images, singles=singles, captioner=flaky)
    second, _ = _run(photos, images=images, singles=singles)
    assert first.paused
    assert first.captioned == 1
    assert not second.paused
    assert second.already_captioned == 1
    assert second.captioned == 1


def test_the_limit_stops_the_run_early():
    report, singles = _run(
        [
            _photo("p1", thumb="t/p1"),
            _photo("p2", 1, thumb="t/p2"),
            _photo("p3", 2, thumb="t/p3"),
        ],
        images={"t/p1": b"1", "t/p2": b"2", "t/p3": b"3"},
        limit=1,
    )
    assert report.captioned == 1


def test_the_oldest_photograph_comes_first():
    report, singles = _run(
        [_photo("old", thumb="t/old"), _photo("new", 60, thumb="t/new")],
        images={"t/old": b"a", "t/new": b"b"},
        limit=1,
    )
    assert singles.get(PhotoId("old")) is not None
    assert singles.get(PhotoId("new")) is None
