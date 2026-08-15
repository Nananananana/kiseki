"""The subject run also reads single-photo captions (ADR-0034)."""

from datetime import UTC, datetime

from kiseki.adapters.fake.captions import FakeCaptionRepository
from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.adapters.fake.singles import FakeSingleCaptionRepository
from kiseki.adapters.fake.subjects import FakeSubjectRepository
from kiseki.application.subject_extraction import run_subject_extraction
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.photo.observation import PhotoId

NOW = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _single(
    identifier: str, text: str = "a bowl of ramen", refused: str | None = None
) -> SingleCaption:
    return SingleCaption(
        photo_id=PhotoId(identifier),
        text="" if refused else text,
        model="" if refused else "qwen3-vl:8b",
        created_at=NOW,
        refused=refused,
    )


def _stay_caption(identifier: str) -> Caption:
    photo_ids = (PhotoId(identifier),)
    return Caption(CaptionKey.of(photo_ids), photo_ids, "a stone temple gate", "vl", NOW)


def _run(
    captions: FakeCaptionRepository,
    subjects: FakeSubjectRepository,
    singles: FakeSingleCaptionRepository | None,
    answer: str = '["ramen"]',
    limit: int | None = None,
):
    return run_subject_extraction(
        captions=captions,
        subjects=subjects,
        language_model=FakeLanguageModel(answer=lambda system, prompt: answer),
        singles=singles,
        limit=limit,
        now=lambda: NOW,
    )


class TestSinglesJoinTheSubjectRun:
    def test_a_single_caption_is_read_under_its_photograph_key(self) -> None:
        singles = FakeSingleCaptionRepository()
        singles.save(_single("sha256:aa"))
        subjects = FakeSubjectRepository()
        report = _run(FakeCaptionRepository(), subjects, singles)
        assert report.extracted == 1
        reading = subjects.get(CaptionKey.of([PhotoId("sha256:aa")]))
        assert reading is not None
        assert reading.labels == ("ramen",)

    def test_stays_and_singles_share_one_run(self) -> None:
        captions = FakeCaptionRepository()
        captions.save(_stay_caption("sha256:aa"))
        singles = FakeSingleCaptionRepository()
        singles.save(_single("sha256:bb"))
        subjects = FakeSubjectRepository()
        report = _run(captions, subjects, singles)
        assert report.extracted == 2

    def test_a_second_run_skips_the_finished_single(self) -> None:
        singles = FakeSingleCaptionRepository()
        singles.save(_single("sha256:aa"))
        subjects = FakeSubjectRepository()
        _run(FakeCaptionRepository(), subjects, singles)
        report = _run(FakeCaptionRepository(), subjects, singles)
        assert report.extracted == 0
        assert report.already_extracted == 1

    def test_a_refused_single_caption_is_left_alone(self) -> None:
        singles = FakeSingleCaptionRepository()
        singles.save(_single("sha256:aa", refused="no thumbnail"))
        subjects = FakeSubjectRepository()
        report = _run(FakeCaptionRepository(), subjects, singles)
        assert report.extracted == 0
        assert subjects.all() == ()

    def test_without_singles_the_run_is_unchanged(self) -> None:
        captions = FakeCaptionRepository()
        captions.save(_stay_caption("sha256:aa"))
        subjects = FakeSubjectRepository()
        report = _run(captions, subjects, None)
        assert report.extracted == 1

    def test_the_limit_spans_stays_and_singles(self) -> None:
        captions = FakeCaptionRepository()
        captions.save(_stay_caption("sha256:aa"))
        singles = FakeSingleCaptionRepository()
        singles.save(_single("sha256:bb"))
        subjects = FakeSubjectRepository()
        first = _run(captions, subjects, singles, limit=1)
        assert first.extracted == 1
        second = _run(captions, subjects, singles)
        assert second.already_extracted == 1
        assert second.extracted == 1
