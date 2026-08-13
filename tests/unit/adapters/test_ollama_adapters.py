"""The Ollama adapters, exercised without an Ollama.

The HTTP transport is injected, so what is specified here is
everything the adapter itself decides: the shape of the payload, the
mapping from HTTP status to the two exception types, and the usage
accounting. A running Ollama is exercised by the llm-marked contract
tests, which CI never runs.
"""

import base64
from typing import Any

import pytest
from kiseki.adapters.ollama.models import (
    OllamaImageCaptioner,
    OllamaLanguageModel,
    OllamaTextEmbedder,
    _error_for,
)
from kiseki.ports.models import (
    CaptionRequest,
    ModelRefusedError,
    ModelUnavailableError,
)

CHAT_ANSWER: dict[str, Any] = {
    "model": "answering-model",
    "message": {"content": "a red square"},
    "prompt_eval_count": 10,
    "eval_count": 5,
}


class RecordingPost:
    """Stands in for the HTTP transport and records every call."""

    def __init__(self, answer: Any) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._answer = answer

    def __call__(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((path, payload))
        if isinstance(self._answer, Exception):
            raise self._answer
        assert isinstance(self._answer, dict)
        return self._answer


class TestErrorMapping:
    def test_a_server_error_means_retrying_may_work(self) -> None:
        assert isinstance(_error_for(500, "boom"), ModelUnavailableError)

    def test_a_rate_limit_means_retrying_may_work(self) -> None:
        assert isinstance(_error_for(429, "slow down"), ModelUnavailableError)

    def test_a_timeout_status_means_retrying_may_work(self) -> None:
        assert isinstance(_error_for(408, "timed out"), ModelUnavailableError)

    def test_a_bad_request_means_retrying_will_not(self) -> None:
        assert isinstance(_error_for(400, "malformed"), ModelRefusedError)

    def test_an_unknown_model_means_retrying_will_not(self) -> None:
        assert isinstance(_error_for(404, "model not found"), ModelRefusedError)


class TestOllamaImageCaptioner:
    def test_sends_the_images_base64_encoded(self) -> None:
        post = RecordingPost(CHAT_ANSWER)
        OllamaImageCaptioner(post=post).caption([CaptionRequest((b"pixels",), "describe")])
        path, payload = post.calls[0]
        assert path == "/api/chat"
        expected = [base64.b64encode(b"pixels").decode("ascii")]
        assert payload["messages"][0]["images"] == expected

    def test_prepends_the_context_to_the_prompt(self) -> None:
        post = RecordingPost(CHAT_ANSWER)
        request = CaptionRequest((b"pixels",), "describe", context="Kyoto, a rainy morning")
        OllamaImageCaptioner(post=post).caption([request])
        content = post.calls[0][1]["messages"][0]["content"]
        assert content.startswith("Kyoto, a rainy morning")
        assert content.endswith("describe")

    def test_without_context_the_prompt_stands_alone(self) -> None:
        post = RecordingPost(CHAT_ANSWER)
        OllamaImageCaptioner(post=post).caption([CaptionRequest((b"pixels",), "describe")])
        assert post.calls[0][1]["messages"][0]["content"] == "describe"

    def test_asks_for_one_answer_and_releases_the_model(self) -> None:
        post = RecordingPost(CHAT_ANSWER)
        OllamaImageCaptioner(model="m", keep_alive="0", post=post).caption(
            [CaptionRequest((b"pixels",), "describe")]
        )
        payload = post.calls[0][1]
        assert payload["model"] == "m"
        assert payload["stream"] is False
        assert payload["keep_alive"] == "0"

    def test_reads_the_answer_and_its_cost(self) -> None:
        post = RecordingPost(CHAT_ANSWER)
        captioner = OllamaImageCaptioner(post=post)
        result = captioner.caption([CaptionRequest((b"pixels",), "describe")])[0]
        assert result.text == "a red square"
        assert result.model == "answering-model"
        assert result.input_tokens == 10
        assert result.output_tokens == 5

    def test_usage_accumulates_across_requests(self) -> None:
        post = RecordingPost(CHAT_ANSWER)
        captioner = OllamaImageCaptioner(post=post)
        captioner.caption(
            [CaptionRequest((b"one",), "describe"), CaptionRequest((b"two",), "describe")]
        )
        assert captioner.usage.calls == 2
        assert captioner.usage.input_tokens == 20
        assert captioner.usage.output_tokens == 10

    def test_a_raised_error_is_counted_and_passed_on(self) -> None:
        post = RecordingPost(ModelRefusedError("image too large"))
        captioner = OllamaImageCaptioner(post=post)
        with pytest.raises(ModelRefusedError):
            captioner.caption([CaptionRequest((b"pixels",), "describe")])
        assert captioner.usage.failures == 1


class TestOllamaLanguageModel:
    def test_sends_the_system_and_the_prompt_as_messages(self) -> None:
        post = RecordingPost(CHAT_ANSWER)
        OllamaLanguageModel(post=post).complete("be brief", ["a question"])
        payload = post.calls[0][1]
        assert payload["messages"] == [
            {"role": "system", "content": "be brief"},
            {"role": "user", "content": "a question"},
        ]

    def test_one_call_per_prompt(self) -> None:
        post = RecordingPost(CHAT_ANSWER)
        model = OllamaLanguageModel(post=post)
        model.complete("be brief", ["one", "two"])
        assert len(post.calls) == 2
        assert model.usage.calls == 2


class TestOllamaTextEmbedder:
    def test_sends_the_whole_batch_in_one_request(self) -> None:
        post = RecordingPost({"embeddings": [[1.0, 0.0], [0.0, 1.0]]})
        OllamaTextEmbedder(dimensions=2, post=post).embed(["one", "two"])
        path, payload = post.calls[0]
        assert path == "/api/embed"
        assert payload["input"] == ["one", "two"]
        assert len(post.calls) == 1

    def test_normalises_what_comes_back(self) -> None:
        post = RecordingPost({"embeddings": [[3.0, 4.0]]})
        vector = OllamaTextEmbedder(dimensions=2, post=post).embed(["text"])[0]
        assert vector == pytest.approx((0.6, 0.8))

    def test_refuses_a_vector_of_the_wrong_width(self) -> None:
        post = RecordingPost({"embeddings": [[1.0, 2.0, 3.0]]})
        with pytest.raises(ModelRefusedError):
            OllamaTextEmbedder(dimensions=2, post=post).embed(["text"])

    def test_refuses_a_short_answer(self) -> None:
        post = RecordingPost({"embeddings": [[1.0, 0.0]]})
        with pytest.raises(ModelRefusedError):
            OllamaTextEmbedder(dimensions=2, post=post).embed(["one", "two"])

    def test_an_empty_batch_makes_no_call(self) -> None:
        post = RecordingPost({"embeddings": []})
        assert OllamaTextEmbedder(dimensions=2, post=post).embed([]) == []
        assert post.calls == []
