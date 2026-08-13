"""Stage two: read each caption once, name its subjects, resumably."""

from collections.abc import Sequence
from datetime import UTC, datetime

from kiseki.adapters.fake.captions import FakeCaptionRepository
from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.adapters.fake.subjects import FakeSubjectRepository
from kiseki.application.subject_extraction import (
    SubjectRunReport,
    parse_subject_labels,
    run_subject_extraction,
)
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.photo.observation import PhotoId
from kiseki.ports.models import Completion, ModelRefusedError, Usage

NOW = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _caption(identifier: str, text: str = "a bowl of ramen", refused: str | None = None) -> Caption:
    photo_ids = (PhotoId(identifier),)
    return Caption(
        key=CaptionKey.of(photo_ids),
        photo_ids=photo_ids,
        text="" if refused else text,
        model="" if refused else "qwen3-vl:8b",
        created_at=NOW,
        refused=refused,
    )


class RefusingLanguageModel:
    """Declines every prompt, as a hosted service might."""

    def complete(self, system: str, prompts: Sequence[str]) -> list[Completion]:
        raise ModelRefusedError("content declined")

    @property
    def usage(self) -> Usage:
        return Usage()


class World:
    def __init__(self, *captions: Caption) -> None:
        self.captions = FakeCaptionRepository()
        for caption in captions:
            self.captions.save(caption)
        self.subjects = FakeSubjectRepository()

    def run(self, language_model: object, **kwargs: object) -> SubjectRunReport:
        return run_subject_extraction(
            captions=self.captions,
            subjects=self.subjects,
            language_model=language_model,  # type: ignore[arg-type]
            now=lambda: NOW,
            **kwargs,  # type: ignore[arg-type]
        )


class TestParseSubjectLabels:
    def test_reads_a_plain_json_array(self) -> None:
        assert parse_subject_labels('["ramen", "noodle soup"]') == ("ramen", "noodle soup")

    def test_reads_an_array_inside_a_code_fence(self) -> None:
        answer = '```json\n["ramen"]\n```'
        assert parse_subject_labels(answer) == ("ramen",)

    def test_reads_an_array_surrounded_by_prose(self) -> None:
        answer = 'Here are the subjects: ["ramen", "counter"] I hope this helps.'
        assert parse_subject_labels(answer) == ("ramen", "counter")

    def test_normalises_case_and_duplicates(self) -> None:
        assert parse_subject_labels('["Ramen", " ramen ", "Counter"]') == ("ramen", "counter")

    def test_caps_the_number_of_labels(self) -> None:
        answer = '["a", "b", "c", "d", "e", "f", "g"]'
        assert len(parse_subject_labels(answer)) == 5

    def test_ignores_items_that_are_not_text(self) -> None:
        assert parse_subject_labels('["ramen", 3, null]') == ("ramen",)

    def test_an_answer_without_an_array_is_empty(self) -> None:
        assert parse_subject_labels("no structure here") == ()


class TestSubjectRun:
    def test_an_empty_store_reports_zeros(self) -> None:
        world = World()
        report = world.run(FakeLanguageModel())
        assert report == SubjectRunReport(0, 0, 0, False)

    def test_reads_a_caption_and_keeps_the_labels(self) -> None:
        world = World(_caption("sha256:aa"))
        model = FakeLanguageModel(answer=lambda system, prompt: '["ramen", "noodle soup"]')
        report = world.run(model)
        assert report.extracted == 1
        reading = world.subjects.all()[0]
        assert reading.answered
        assert reading.labels == ("ramen", "noodle soup")
        assert reading.key == _caption("sha256:aa").key
        assert reading.model == "fake-language-model"

    def test_a_second_run_skips_what_is_done(self) -> None:
        world = World(_caption("sha256:aa"))
        model = FakeLanguageModel(answer=lambda system, prompt: '["ramen"]')
        world.run(model)
        report = world.run(model)
        assert report.extracted == 0
        assert report.already_extracted == 1

    def test_a_refused_caption_is_left_alone(self) -> None:
        world = World(_caption("sha256:aa", refused="image too large"))
        report = world.run(FakeLanguageModel(answer=lambda system, prompt: '["ramen"]'))
        assert report == SubjectRunReport(0, 0, 0, False)
        assert world.subjects.all() == ()

    def test_an_unparseable_answer_is_recorded_and_not_asked_again(self) -> None:
        world = World(_caption("sha256:aa"))
        first = world.run(FakeLanguageModel(answer=lambda system, prompt: "no json"))
        assert first.refused == 1
        assert not world.subjects.all()[0].answered

        second = world.run(FakeLanguageModel(answer=lambda system, prompt: '["ramen"]'))
        assert second.already_extracted == 1
        assert second.extracted == 0

    def test_a_model_refusal_is_recorded(self) -> None:
        world = World(_caption("sha256:aa"))
        report = world.run(RefusingLanguageModel())
        assert report.refused == 1
        assert not world.subjects.all()[0].answered

    def test_an_unavailable_model_pauses_and_a_rerun_resumes(self) -> None:
        first_caption = _caption("sha256:aa", text="a bowl of ramen")
        second_caption = _caption("sha256:bb", text="a stone temple gate")
        world = World(first_caption, second_caption)

        failing = FakeLanguageModel(
            answer=lambda system, prompt: '["ramen"]',
            fail_on=lambda prompt: "temple" in prompt,
        )
        first = world.run(failing)
        assert first.extracted == 1
        assert first.paused

        second = world.run(FakeLanguageModel(answer=lambda system, prompt: '["temple gate"]'))
        assert second.already_extracted == 1
        assert second.extracted == 1
        assert not second.paused

    def test_the_limit_bounds_the_work(self) -> None:
        world = World(_caption("sha256:aa"), _caption("sha256:bb"), _caption("sha256:cc"))
        model = FakeLanguageModel(answer=lambda system, prompt: '["ramen"]')
        first = world.run(model, limit=1)
        assert first.extracted == 1

        second = world.run(model)
        assert second.already_extracted == 1
        assert second.extracted == 2
