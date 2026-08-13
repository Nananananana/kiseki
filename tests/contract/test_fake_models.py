"""The fakes must satisfy the same contract a real adapter will."""

import pytest
from kiseki.adapters.fake.models import (
    FakeImageCaptioner,
    FakeLanguageModel,
    FakeTextEmbedder,
)
from kiseki.ports.models import CaptionRequest, ModelUnavailableError
from model_contract import (
    ImageCaptionerContract,
    LanguageModelContract,
    TextEmbedderContract,
)


class TestFakeImageCaptioner(ImageCaptionerContract):
    @pytest.fixture
    def captioner(self) -> FakeImageCaptioner:
        return FakeImageCaptioner()


class TestFakeLanguageModel(LanguageModelContract):
    @pytest.fixture
    def language_model(self) -> FakeLanguageModel:
        return FakeLanguageModel()


class TestFakeTextEmbedder(TextEmbedderContract):
    @pytest.fixture
    def embedder(self) -> FakeTextEmbedder:
        return FakeTextEmbedder()


class TestFakesAreControllable:
    """What a fake must offer beyond the contract, to be useful in a test."""

    def test_a_caption_can_be_scripted(self) -> None:
        captioner = FakeImageCaptioner(describe=lambda request: f"scripted {request.prompt}")
        assert captioner.caption([CaptionRequest((b"image",), "X")])[0].text == "scripted X"

    def test_an_answer_can_be_scripted(self) -> None:
        """Testing a JSON parser needs a model that returns known JSON."""
        model = FakeLanguageModel(answer=lambda system, prompt: '{"ok": true}')
        assert model.complete("s", ["p"])[0].text == '{"ok": true}'

    def test_it_records_what_it_was_asked(self) -> None:
        captioner = FakeImageCaptioner()
        captioner.caption([CaptionRequest((b"image",), "a prompt", context="at a park")])
        assert captioner.seen[0].context == "at a park"

    def test_a_failure_can_be_provoked(self) -> None:
        """Resumable batching cannot be tested without a way to fail."""
        captioner = FakeImageCaptioner(fail_on=lambda request: b"bad" in request.images[0])
        with pytest.raises(ModelUnavailableError):
            captioner.caption([CaptionRequest((b"bad image",), "describe")])

    def test_a_failure_is_counted(self) -> None:
        captioner = FakeImageCaptioner(fail_on=lambda request: True)
        with pytest.raises(ModelUnavailableError):
            captioner.caption([CaptionRequest((b"image",), "describe")])
        assert captioner.usage.failures == 1

    def test_captions_differ_by_image(self) -> None:
        captioner = FakeImageCaptioner()
        results = captioner.caption(
            [CaptionRequest((b"one",), "describe"), CaptionRequest((b"two",), "describe")]
        )
        assert results[0].text != results[1].text
