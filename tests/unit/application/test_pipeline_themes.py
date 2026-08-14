"""The pipeline applies the latest stored theme set to the profile."""

from datetime import datetime, timezone

from kiseki.adapters.fake.captions import FakeCaptionRepository
from kiseki.adapters.fake.subjects import FakeSubjectRepository
from kiseki.adapters.fake.themes import FakeThemeSetRepository
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.caption.themes import Theme, ThemeSet, ThemeSetKey
from kiseki.domain.photo.observation import PhotoId, PhotoObservation

NOW = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)
WHEN = datetime(2026, 5, 3, 10, tzinfo=timezone.utc)


def _pipeline(themes: FakeThemeSetRepository | None) -> Pipeline:
    photos = InMemoryPhotoRepository()
    photos.save_all(
        [
            PhotoObservation(PhotoId("sha256:aa"), WHEN),
            PhotoObservation(PhotoId("sha256:bb"), WHEN),
        ]
    )
    captions = FakeCaptionRepository()
    subjects = FakeSubjectRepository()
    for identifier, labels in [("sha256:aa", ("tree",)), ("sha256:bb", ("landscape",))]:
        photo_ids = (PhotoId(identifier),)
        caption = Caption(CaptionKey.of(photo_ids), photo_ids, "a scene", "vl", NOW)
        captions.save(caption)
        subjects.save(SubjectExtraction(caption.key, labels, "lm", NOW))
    return Pipeline(
        photos,
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        captions=captions,
        subjects=subjects,
        themes=themes,
    )


def _stored_theme_set() -> FakeThemeSetRepository:
    repository = FakeThemeSetRepository()
    repository.save(
        ThemeSet(
            key=ThemeSetKey.of(["landscape", "tree"]),
            themes=(Theme(name="outdoor", members=("tree", "landscape")),),
            model="lm",
            created_at=NOW,
        )
    )
    return repository


class TestPipelineThemes:
    def test_the_latest_theme_set_shapes_the_profile(self) -> None:
        pipeline = _pipeline(_stored_theme_set())
        topics = [i.topic for i in pipeline.profile(generated_at=NOW).interests]
        assert topics == ["outdoor"]

    def test_without_a_repository_labels_speak_solo(self) -> None:
        pipeline = _pipeline(None)
        topics = [i.topic for i in pipeline.profile(generated_at=NOW).interests]
        assert sorted(topics) == ["landscape", "tree"]

    def test_an_empty_repository_changes_nothing(self) -> None:
        pipeline = _pipeline(FakeThemeSetRepository())
        topics = [i.topic for i in pipeline.profile(generated_at=NOW).interests]
        assert sorted(topics) == ["landscape", "tree"]
