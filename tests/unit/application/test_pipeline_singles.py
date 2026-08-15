"""The pipeline merges single-photo subjects into the one profile."""

from datetime import UTC, datetime

from kiseki.adapters.fake.captions import FakeCaptionRepository
from kiseki.adapters.fake.singles import FakeSingleCaptionRepository
from kiseki.adapters.fake.subjects import FakeSubjectRepository
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline
from kiseki.domain.caption.caption import CaptionKey
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.photo.observation import PhotoId, PhotoObservation

NOW = datetime(2026, 6, 1, 12, tzinfo=UTC)
WHEN = datetime(2026, 5, 3, 10, tzinfo=UTC)


def _pipeline(with_singles: bool) -> Pipeline:
    photos = InMemoryPhotoRepository()
    photos.save_all([PhotoObservation(PhotoId("sha256:aa"), WHEN)])

    singles = FakeSingleCaptionRepository()
    singles.save(SingleCaption(PhotoId("sha256:aa"), "a bowl of ramen", "vl", NOW))

    subjects = FakeSubjectRepository()
    subjects.save(SubjectExtraction(CaptionKey.of([PhotoId("sha256:aa")]), ("ramen",), "lm", NOW))

    return Pipeline(
        photos,
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        captions=FakeCaptionRepository(),
        subjects=subjects,
        singles=singles if with_singles else None,
    )


class TestPipelineSingles:
    def test_single_subjects_join_the_profile(self) -> None:
        profile = _pipeline(with_singles=True).profile(generated_at=NOW)
        assert [interest.topic for interest in profile.interests] == ["ramen"]

    def test_without_a_singles_repository_the_reading_is_ignored(self) -> None:
        profile = _pipeline(with_singles=False).profile(generated_at=NOW)
        assert profile.interests == ()
