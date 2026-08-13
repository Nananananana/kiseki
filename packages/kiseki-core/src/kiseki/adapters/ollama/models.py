"""Ollama adapters for the model ports.

Speaks to a local Ollama over HTTP using nothing but the standard
library, so kiseki-core keeps declaring no runtime dependencies; like
sqlite3 for storage, urllib is the whole transport.

The transport is injectable. The unit tests exercise every decision
the adapter makes -- payload shape, error mapping, usage accounting --
against a recorded stand-in, and only the llm-marked contract tests
speak to a running Ollama. The error mapping follows ADR-0015: what
may succeed on a retry raises ModelUnavailableError, what will not
raises ModelRefusedError. keep_alive is explicit per ADR-0014, so one
stage does not deny the next its memory.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from typing import Any

from kiseki.ports.models import (
    CaptionRequest,
    Completion,
    ModelRefusedError,
    ModelUnavailableError,
    Usage,
)

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_KEEP_ALIVE = "5m"
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_CAPTIONING_MODEL = "qwen3-vl:8b"
DEFAULT_LANGUAGE_MODEL = "qwen2.5:14b-instruct-q4_K_M"
DEFAULT_EMBEDDING_MODEL = "bge-m3"
DEFAULT_EMBEDDING_DIMENSIONS = 1024

RETRYABLE_STATUSES = (408, 429)

Post = Callable[[str, dict[str, Any]], dict[str, Any]]
"""The transport: POST a JSON payload to a path, return the JSON answer."""


def _error_for(status: int, detail: str) -> RuntimeError:
    """Type an HTTP failure by whether retrying could change the answer."""
    if status in RETRYABLE_STATUSES or status >= 500:
        return ModelUnavailableError(f"ollama answered {status}: {detail}")
    return ModelRefusedError(f"ollama answered {status}: {detail}")


def _http_post(host: str, timeout: float) -> Post:
    def post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            host + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                document: dict[str, Any] = json.loads(response.read().decode("utf-8"))
                return document
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:200]
            raise _error_for(error.code, detail) from error
        except OSError as error:
            raise ModelUnavailableError(f"cannot reach ollama at {host}: {error}") from error

    return post


class _ChatAdapter:
    """Shared machinery for the two adapters that use the chat endpoint."""

    def __init__(self, model: str, keep_alive: str, post: Post) -> None:
        self._model = model
        self._keep_alive = keep_alive
        self._post = post
        self._usage = Usage()

    def _ask(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": self._model,
            "stream": False,
            "keep_alive": self._keep_alive,
            "messages": messages,
        }
        try:
            return self._post("/api/chat", payload)
        except (ModelUnavailableError, ModelRefusedError):
            self._usage = self._usage.record_failure()
            raise

    def _record(self, document: dict[str, Any]) -> Completion:
        completion = Completion(
            text=document.get("message", {}).get("content", ""),
            model=document.get("model", self._model),
            input_tokens=int(document.get("prompt_eval_count", 0)),
            output_tokens=int(document.get("eval_count", 0)),
        )
        self._usage = self._usage.record(completion)
        return completion

    @property
    def usage(self) -> Usage:
        return self._usage


class OllamaImageCaptioner(_ChatAdapter):
    """Captions photographs through Ollama's chat endpoint."""

    def __init__(
        self,
        model: str = DEFAULT_CAPTIONING_MODEL,
        host: str = DEFAULT_HOST,
        keep_alive: str = DEFAULT_KEEP_ALIVE,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        post: Post | None = None,
    ) -> None:
        super().__init__(model, keep_alive, post if post is not None else _http_post(host, timeout))

    def caption(self, requests: Sequence[CaptionRequest]) -> list[Completion]:
        completions = []
        for request in requests:
            content = (
                f"{request.context}\n\n{request.prompt}" if request.context else request.prompt
            )
            message = {
                "role": "user",
                "content": content,
                "images": [base64.b64encode(image).decode("ascii") for image in request.images],
            }
            completions.append(self._record(self._ask([message])))
        return completions


class OllamaLanguageModel(_ChatAdapter):
    """Writes prose through Ollama's chat endpoint."""

    def __init__(
        self,
        model: str = DEFAULT_LANGUAGE_MODEL,
        host: str = DEFAULT_HOST,
        keep_alive: str = DEFAULT_KEEP_ALIVE,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        post: Post | None = None,
    ) -> None:
        super().__init__(model, keep_alive, post if post is not None else _http_post(host, timeout))

    def complete(self, system: str, prompts: Sequence[str]) -> list[Completion]:
        completions = []
        for prompt in prompts:
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            completions.append(self._record(self._ask(messages)))
        return completions


class OllamaTextEmbedder:
    """Embeds text through Ollama's embed endpoint, normalising the vectors.

    Normalisation happens here rather than being assumed of the model,
    because the contract promises unit vectors and a promise the
    adapter can keep itself should not depend on the model behind it.
    """

    def __init__(
        self,
        model: str = DEFAULT_EMBEDDING_MODEL,
        dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
        host: str = DEFAULT_HOST,
        keep_alive: str = DEFAULT_KEEP_ALIVE,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        post: Post | None = None,
    ) -> None:
        if dimensions < 1:
            raise ValueError("an embedder needs at least one dimension")
        self._model = model
        self._dimensions = dimensions
        self._keep_alive = keep_alive
        self._post = post if post is not None else _http_post(host, timeout)

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        if not texts:
            return []
        payload = {
            "model": self._model,
            "keep_alive": self._keep_alive,
            "input": list(texts),
        }
        document = self._post("/api/embed", payload)
        rows = document.get("embeddings", [])
        vectors = [self._normalised(row) for row in rows]
        if len(vectors) != len(texts):
            raise ModelRefusedError(f"asked for {len(texts)} vectors, got {len(vectors)}")
        return vectors

    def _normalised(self, row: Sequence[float]) -> tuple[float, ...]:
        vector = tuple(float(value) for value in row)
        if len(vector) != self._dimensions:
            raise ModelRefusedError(
                f"model returned {len(vector)} dimensions, expected {self._dimensions}"
            )
        length = sum(value * value for value in vector) ** 0.5 or 1.0
        return tuple(value / length for value in vector)

    @property
    def dimensions(self) -> int:
        return self._dimensions
