"""Contract suites every model implementation must satisfy.

Applied to the fakes now, and to the Ollama adapter in issue #18. Anything an
adapter for a hosted service would also have to honour belongs here: batching,
ordering, usage accounting, and which exception means retry.
"""

import pytest

from kiseki.ports.models import (
    CaptionRequest,
    ImageCaptioner,
    LanguageModel,
    TextEmbedder,
)


class ImageCaptionerContract:
    @pytest.fixture
    def captioner(self) -> ImageCaptioner:
        raise NotImplementedError("override the 'captioner' fixture")

    def test_returns_one_completion_per_request(self, captioner: ImageCaptioner) -> None:
        requests = [
            CaptionRequest((b"first",), "describe"),
            CaptionRequest((b"second",), "describe"),
        ]
        assert len(captioner.caption(requests)) == 2

    def test_preserves_the_order_of_the_batch(self, captioner: ImageCaptioner) -> None:
        """Results are matched back to stops by position."""
        requests = [CaptionRequest((f"image{index}".encode(),), "describe") for index in range(4)]
        results = captioner.caption(requests)
        assert len(results) == 4
        assert len({result.text for result in results}) == 4

    def test_an_empty_batch_is_allowed(self, captioner: ImageCaptioner) -> None:
        assert captioner.caption([]) == []

    def test_produces_some_text(self, captioner: ImageCaptioner) -> None:
        result = captioner.caption([CaptionRequest((b"image",), "describe")])[0]
        assert result.text.strip()

    def test_records_which_model_answered(self, captioner: ImageCaptioner) -> None:
        result = captioner.caption([CaptionRequest((b"image",), "describe")])[0]
        assert result.model.strip()

    def test_accepts_several_images_in_one_request(self, captioner: ImageCaptioner) -> None:
        """A stop is described from several representative photographs at once."""
        request = CaptionRequest((b"one", b"two", b"three"), "describe these")
        assert captioner.caption([request])[0].text.strip()

    def test_counts_what_it_was_asked_to_do(self, captioner: ImageCaptioner) -> None:
        before = captioner.usage.calls
        captioner.caption([CaptionRequest((b"image",), "describe")])
        assert captioner.usage.calls == before + 1


class LanguageModelContract:
    @pytest.fixture
    def language_model(self) -> LanguageModel:
        raise NotImplementedError("override the 'language_model' fixture")

    def test_returns_one_completion_per_prompt(self, language_model: LanguageModel) -> None:
        assert len(language_model.complete("be brief", ["one", "two"])) == 2

    def test_an_empty_batch_is_allowed(self, language_model: LanguageModel) -> None:
        assert language_model.complete("be brief", []) == []

    def test_produces_some_text(self, language_model: LanguageModel) -> None:
        assert language_model.complete("be brief", ["a question"])[0].text.strip()

    def test_records_which_model_answered(self, language_model: LanguageModel) -> None:
        assert language_model.complete("be brief", ["a question"])[0].model.strip()

    def test_counts_what_it_was_asked_to_do(self, language_model: LanguageModel) -> None:
        before = language_model.usage.calls
        language_model.complete("be brief", ["one", "two"])
        assert language_model.usage.calls == before + 2


class TextEmbedderContract:
    @pytest.fixture
    def embedder(self) -> TextEmbedder:
        raise NotImplementedError("override the 'embedder' fixture")

    def test_returns_one_vector_per_text(self, embedder: TextEmbedder) -> None:
        assert len(embedder.embed(["one", "two", "three"])) == 3

    def test_an_empty_batch_is_allowed(self, embedder: TextEmbedder) -> None:
        assert embedder.embed([]) == []

    def test_every_vector_has_the_declared_width(self, embedder: TextEmbedder) -> None:
        """A stored index is unusable if the width ever changes."""
        vectors = embedder.embed(["one", "two"])
        assert all(len(vector) == embedder.dimensions for vector in vectors)

    def test_the_same_text_gives_the_same_vector(self, embedder: TextEmbedder) -> None:
        assert embedder.embed(["repeatable"]) == embedder.embed(["repeatable"])

    def test_different_texts_give_different_vectors(self, embedder: TextEmbedder) -> None:
        first, second = embedder.embed(["one thing", "another thing entirely"])
        assert first != second

    def test_vectors_are_normalised(self, embedder: TextEmbedder) -> None:
        """Cosine similarity reduces to a dot product only if they are."""
        vector = embedder.embed(["some text"])[0]
        length = sum(value * value for value in vector) ** 0.5
        assert length == pytest.approx(1.0, abs=1e-6)


__all__ = [
    "ImageCaptionerContract",
    "LanguageModelContract",
    "TextEmbedderContract",
]
