"""The Ollama screen reader: one image in, category and labels out.

The adapter owns the prompt and the parsing; the raw answer never
leaves it. Exercised against an injected transport. See ADR-0030.
"""

import json
from typing import Any

import pytest
from kiseki.adapters.ollama.screens import OllamaScreenshotReader
from kiseki.ports.models import ModelRefusedError


def _post_answering(content: str) -> Any:
    def post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
        post.paths.append(path)  # type: ignore[attr-defined]
        post.payloads.append(payload)  # type: ignore[attr-defined]
        return {"message": {"content": content}, "model": "qwen3-vl:8b"}

    post.paths = []  # type: ignore[attr-defined]
    post.payloads = []  # type: ignore[attr-defined]
    return post


class TestOllamaScreenshotReader:
    def test_asks_the_chat_endpoint_with_the_image(self) -> None:
        post = _post_answering(json.dumps({"category": "product", "labels": ["camera"]}))
        reader = OllamaScreenshotReader(post=post)
        reader.read([b"img"])
        assert post.paths == ["/api/chat"]
        assert post.payloads[0]["messages"][0]["images"]

    def test_parses_category_and_labels(self) -> None:
        post = _post_answering(json.dumps({"category": "food", "labels": ["Ramen", " "]}))
        (result,) = OllamaScreenshotReader(post=post).read([b"img"])
        assert result.category == "food"
        assert result.labels == ("ramen",)

    def test_tolerates_fences_and_unknown_categories(self) -> None:
        answer = "```json\n" + json.dumps({"category": "horoscope", "labels": ["star"]}) + "\n```"
        (result,) = OllamaScreenshotReader(post=_post_answering(answer)).read([b"img"])
        assert result.category == "other"
        assert result.labels == ("star",)

    def test_a_sensitive_category_loses_its_labels(self) -> None:
        post = _post_answering(json.dumps({"category": "chat", "labels": ["gossip"]}))
        (result,) = OllamaScreenshotReader(post=post).read([b"img"])
        assert result.category == "chat"
        assert result.labels == ()

    def test_an_unparseable_answer_is_a_refusal(self) -> None:
        with pytest.raises(ModelRefusedError):
            OllamaScreenshotReader(post=_post_answering("a poem")).read([b"img"])
