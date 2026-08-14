"""One logical embed batch travels as several modest requests.

Large single requests have crashed Ollama's embedding runner; the
adapter keeps each request small and concatenates the answers in
order. Callers see one batch in, one list out, exactly as before.
"""

from typing import Any

import pytest

from kiseki.adapters.ollama import models
from kiseki.adapters.ollama.models import OllamaTextEmbedder
from kiseki.ports.models import ModelRefusedError


class EchoingPost:
    """Answers every request with one unit vector per input, and
    records the size of each request."""

    def __init__(self) -> None:
        self.sizes: list[int] = []

    def __call__(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        texts = payload["input"]
        self.sizes.append(len(texts))
        # Encode each text's global index in its vector so order
        # survives concatenation checks.
        return {
            "embeddings": [
                [1.0, 0.0] if text.endswith("even") else [0.0, 1.0] for text in texts
            ]
        }


class TestEmbedChunking:
    def test_a_large_batch_is_sent_in_chunks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(models, "EMBED_BATCH_SIZE", 32)
        post = EchoingPost()
        texts = [f"text-{index}" for index in range(70)]
        vectors = OllamaTextEmbedder(dimensions=2, post=post).embed(texts)
        assert post.sizes == [32, 32, 6]
        assert len(vectors) == 70

    def test_the_order_survives_the_chunking(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(models, "EMBED_BATCH_SIZE", 2)
        post = EchoingPost()
        texts = ["a-even", "b-odd", "c-even", "d-odd", "e-even"]
        vectors = OllamaTextEmbedder(dimensions=2, post=post).embed(texts)
        assert post.sizes == [2, 2, 1]
        assert vectors[0] == pytest.approx((1.0, 0.0))
        assert vectors[1] == pytest.approx((0.0, 1.0))
        assert vectors[4] == pytest.approx((1.0, 0.0))

    def test_a_small_batch_is_one_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(models, "EMBED_BATCH_SIZE", 32)
        post = EchoingPost()
        OllamaTextEmbedder(dimensions=2, post=post).embed(["one-even", "two-odd"])
        assert post.sizes == [2]

    def test_a_short_answer_for_a_chunk_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(models, "EMBED_BATCH_SIZE", 2)

        def starving(path: str, payload: dict[str, Any]) -> dict[str, Any]:
            return {"embeddings": [[1.0, 0.0]]}

        with pytest.raises(ModelRefusedError):
            OllamaTextEmbedder(dimensions=2, post=starving).embed(["a", "b", "c"])
