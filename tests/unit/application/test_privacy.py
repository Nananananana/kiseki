"""The privacy report is counted from storage, deterministically."""

from datetime import UTC, datetime

from kiseki.adapters.fake.corrections import FakeCorrectionRepository
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.correction import Correction, CorrectionVerdict
from kiseki.domain.interests import Profile
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.domain.shared.geo import GeoPoint

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


class _Stub:
    """Any repository the report only reads. Ports are protocols."""

    def __init__(self, items):
        self._items = tuple(items)

    def all(self):
        return self._items

    def history(self):
        return self._items


def _pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        kwargs.pop("photos", InMemoryPhotoRepository()),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        **kwargs,
    )


def test_the_counts_come_from_storage():
    photos = InMemoryPhotoRepository()
    pipeline = _pipeline(photos=photos)
    pipeline.ingest(
        [
            PhotoObservation(PhotoId("sha256:aa"), WHEN, GeoPoint(35.0, 135.0)),
            PhotoObservation(PhotoId("sha256:bb"), WHEN, None, use_for_preference=False),
        ]
    )
    report = pipeline.privacy()
    assert report.photographs == 2
    assert report.located == 1
    assert report.withheld_from_preference == 1
    assert report.stay_captions == 0
    assert report.kept_profiles == 0
    assert report.active_exclusions == 0


def test_the_readings_and_refusals_are_counted():
    key = CaptionKey.of([PhotoId("sha256:aa")])
    pipeline = _pipeline(
        captions=_Stub(
            [
                Caption(key, (PhotoId("sha256:aa"),), "", "vl", WHEN, refused="no thumbnail"),
            ]
        ),
        singles=_Stub([SingleCaption(PhotoId("sha256:bb"), "a bowl of ramen", "vl", WHEN)]),
        screens=_Stub(
            [
                ScreenshotReading(PhotoId("sha256:s1"), "map", ("route",), "vl", WHEN, None),
                ScreenshotReading(PhotoId("sha256:s2"), "chat", (), "vl", WHEN, None),
                ScreenshotReading(PhotoId("sha256:s3"), "map", (), "vl", WHEN, "unreadable"),
            ]
        ),
        subjects=_Stub([SubjectExtraction(key, ("ramen",), "lm", WHEN)]),
        profiles=_Stub([Profile(generated_at=WHEN, interests=())]),
    )
    report = pipeline.privacy()
    assert report.stay_captions == 1
    assert report.stay_refused == 1
    assert report.single_captions == 1
    assert report.single_refused == 0
    assert report.screen_readings == 3
    assert report.screens_label_silent == 1
    assert report.subject_readings == 1
    assert report.kept_profiles == 1


def test_the_exclusions_are_counted():
    corrections = FakeCorrectionRepository()
    corrections.add(Correction("topic:data", CorrectionVerdict.EXCLUDED, "", WHEN))
    corrections.add(Correction("topic:cat", CorrectionVerdict.EXCLUDED, "", WHEN))
    corrections.add(Correction("topic:cat", CorrectionVerdict.REINSTATED, "", WHEN))
    report = _pipeline(corrections=corrections).privacy()
    assert report.corrections == 3
    assert report.active_exclusions == 1
