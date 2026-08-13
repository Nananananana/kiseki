"""The pipeline merges subject interests into the one profile."""

from datetime import datetime, timezone

from kiseki.adapters.fake.captions import FakeCaptionRepository
from kiseki.adapters.fake.profiles import FakeProfileRepository
from kiseki.adapters.fake.subjects import FakeSubjectRepository
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.photo.observation import PhotoId, PhotoObservation

NOW = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)
WHEN = datetime(2026, 5, 3, 10, tzinfo=timezone.utc)


def _seeded() -> tuple[Pipeline, FakeProfileRepository]:
    photos = InMemoryPhotoRepository()
    photos.save_all([PhotoObservation(PhotoId("sha256:aa"), WHEN)])

    photo_ids = (PhotoId("sha256:aa"),)
    caption = Caption(CaptionKey.of(photo_ids), photo_ids, "a bowl of ramen", "vl", NOW)
    captions = FakeCaptionRepository()
    captions.save(caption)

    subjects = FakeSubjectRepository()
    subjects.save(SubjectExtraction(caption.key, ("ramen",), "lm", NOW))

    profiles = FakeProfileRepository()
    pipeline = Pipeline(
        photos,
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        profiles=profiles,
        captions=captions,
        subjects=subjects,
    )
    return pipeline, profiles


class TestPipelineSubjects:
    def test_subject_interests_join_the_profile(self) -> None:
        pipeline, _ = _seeded()
        profile = pipeline.profile(generated_at=NOW)
        assert [interest.topic for interest in profile.interests] == ["ramen"]

    def test_the_merged_profile_is_what_gets_saved(self) -> None:
        pipeline, profiles = _seeded()
        saved = pipeline.profile(generated_at=NOW)
        assert profiles.latest() == saved

    def test_without_the_repositories_the_profile_is_places_only(self) -> None:
        pipeline = Pipeline(
            InMemoryPhotoRepository(),
            InMemoryOutingRepository(),
            InMemoryAnchorRepository(),
        )
        assert pipeline.profile(generated_at=NOW).interests == ()
