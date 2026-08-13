"""The captioning run: describe every stay once, resumably.

The caption store is the progress record. What is already there is
skipped, an unavailable model pauses the run, and a refusal is
recorded so it is not asked again. See ADR-0019.
"""

from collections.abc import Sequence
from datetime import datetime, timezone

import pytest

from kiseki.adapters.fake.captions import FakeCaptionRepository
from kiseki.adapters.fake.models import FakeImageCaptioner
from kiseki.adapters.fake.thumbnails import FakeThumbnailSource
from kiseki.adapters.memory.repositories import (
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.captioning import (
    CaptionRunReport,
    representative_photo_ids,
    run_captioning,
)
from kiseki.domain.caption.caption import CaptionKey
from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange
from kiseki.ports.models import (
    CaptionRequest,
    Completion,
    ModelRefusedError,
    Usage,
)

NOW = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)


def _at(hour: int) -> datetime:
    return datetime(2026, 5, 3, hour, tzinfo=timezone.utc)


def _stop(identifiers: Sequence[str], hour: int) -> Stop:
    photo_ids = tuple(PhotoId(value) for value in identifiers)
    return Stop(photo_ids, TimeRange(_at(hour), _at(hour + 1)), GeoPoint(35.0, 135.0))


class RefusingCaptioner:
    """Declines every request, as a hosted service might."""

    def caption(self, requests: Sequence[CaptionRequest]) -> list[Completion]:
        raise ModelRefusedError("content declined")

    @property
    def usage(self) -> Usage:
        return Usage()


class World:
    """One test's worth of repositories, wired together."""

    def __init__(self, stops: Sequence[Stop], references: dict[str, str | None]) -> None:
        self.photos = InMemoryPhotoRepository()
        self.photos.save_all(
            [
                PhotoObservation(PhotoId(identifier), _at(9), thumbnail_ref=reference)
                for identifier, reference in references.items()
            ]
        )
        self.outings = InMemoryOutingRepository()
        if stops:
            self.outings.replace_all([Outing.of(list(stops))])
        self.captions = FakeCaptionRepository()
        self.thumbnails = FakeThumbnailSource(
            {reference: b"pixels-" + reference.encode() for reference in references.values() if reference}
        )

    def run(self, captioner: object, **kwargs: object) -> CaptionRunReport:
        return run_captioning(
            outings=self.outings,
            photos=self.photos,
            captions=self.captions,
            thumbnails=self.thumbnails,
            captioner=captioner,  # type: ignore[arg-type]
            now=lambda: NOW,
            **kwargs,  # type: ignore[arg-type]
        )


class TestRepresentativeSelection:
    def test_a_small_stay_is_taken_whole(self) -> None:
        photo_ids = tuple(PhotoId(f"sha256:{index}") for index in range(2))
        assert representative_photo_ids(photo_ids, 3) == photo_ids

    def test_a_large_stay_is_sampled_from_ends_and_middle(self) -> None:
        photo_ids = tuple(PhotoId(f"sha256:{index}") for index in range(5))
        chosen = representative_photo_ids(photo_ids, 3)
        assert chosen == (photo_ids[0], photo_ids[2], photo_ids[4])

    def test_a_limit_of_one_takes_the_middle(self) -> None:
        photo_ids = tuple(PhotoId(f"sha256:{index}") for index in range(5))
        assert representative_photo_ids(photo_ids, 1) == (photo_ids[2],)

    def test_a_limit_below_one_is_refused(self) -> None:
        with pytest.raises(ValueError):
            representative_photo_ids((PhotoId("sha256:aa"),), 0)


class TestCaptioningRun:
    def test_an_empty_library_reports_zeros(self) -> None:
        world = World([], {})
        report = world.run(FakeImageCaptioner())
        assert report == CaptionRunReport(0, 0, 0, 0, False)

    def test_captions_a_stay_and_keeps_the_reading(self) -> None:
        world = World(
            [_stop(["sha256:aa", "sha256:bb"], 10)],
            {"sha256:aa": "a.jpg", "sha256:bb": "b.jpg"},
        )
        report = world.run(FakeImageCaptioner())
        assert report.captioned == 1
        caption = world.captions.all()[0]
        assert caption.answered
        assert caption.model == "fake-captioner"
        assert caption.key == CaptionKey.of([PhotoId("sha256:aa"), PhotoId("sha256:bb")])

    def test_a_second_run_skips_what_is_done(self) -> None:
        world = World([_stop(["sha256:aa"], 10)], {"sha256:aa": "a.jpg"})
        world.run(FakeImageCaptioner())
        report = world.run(FakeImageCaptioner())
        assert report.captioned == 0
        assert report.already_captioned == 1

    def test_an_unavailable_model_pauses_and_a_rerun_resumes(self) -> None:
        world = World(
            [_stop(["sha256:aa"], 10), _stop(["sha256:bb"], 14)],
            {"sha256:aa": "a.jpg", "sha256:bb": "b.jpg"},
        )
        failing = FakeImageCaptioner(fail_on=lambda request: b"pixels-b.jpg" in request.images)
        first = world.run(failing)
        assert first.captioned == 1
        assert first.paused

        second = world.run(FakeImageCaptioner())
        assert second.already_captioned == 1
        assert second.captioned == 1
        assert not second.paused

    def test_a_refusal_is_recorded_and_not_asked_again(self) -> None:
        world = World([_stop(["sha256:aa"], 10)], {"sha256:aa": "a.jpg"})
        first = world.run(RefusingCaptioner())
        assert first.refused == 1
        assert not world.captions.all()[0].answered

        second = world.run(FakeImageCaptioner())
        assert second.already_captioned == 1
        assert second.captioned == 0

    def test_a_missing_thumbnail_is_recorded_as_refused(self) -> None:
        world = World([_stop(["sha256:aa"], 10)], {"sha256:aa": "a.jpg"})
        world.thumbnails = FakeThumbnailSource({})
        report = world.run(FakeImageCaptioner())
        assert report.refused == 1
        assert not world.captions.all()[0].answered

    def test_photographs_without_references_are_left_out(self) -> None:
        world = World(
            [_stop(["sha256:aa", "sha256:bb", "sha256:cc"], 10)],
            {"sha256:aa": "a.jpg", "sha256:bb": None, "sha256:cc": "c.jpg"},
        )
        captioner = FakeImageCaptioner()
        world.run(captioner)
        assert len(captioner.seen[0].images) == 2

    def test_a_stay_with_no_references_is_reported(self) -> None:
        world = World([_stop(["sha256:aa"], 10)], {"sha256:aa": None})
        report = world.run(FakeImageCaptioner())
        assert report.unreferenced == 1
        assert world.captions.all() == ()

    def test_the_limit_bounds_the_work(self) -> None:
        world = World(
            [_stop(["sha256:aa"], 8), _stop(["sha256:bb"], 12), _stop(["sha256:cc"], 16)],
            {"sha256:aa": "a.jpg", "sha256:bb": "b.jpg", "sha256:cc": "c.jpg"},
        )
        first = world.run(FakeImageCaptioner(), limit=1)
        assert first.captioned == 1

        second = world.run(FakeImageCaptioner())
        assert second.already_captioned == 1
        assert second.captioned == 2

    def test_the_context_names_when_the_stay_happened(self) -> None:
        world = World([_stop(["sha256:aa"], 10)], {"sha256:aa": "a.jpg"})
        captioner = FakeImageCaptioner()
        world.run(captioner)
        assert "2026-05-03" in captioner.seen[0].context
