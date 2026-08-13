"""Deterministic stand-ins for the models.

Held to the same contract as a real adapter, so they cannot drift from it, and
controllable in ways a real model is not: an answer can be scripted, and a
failure can be provoked. Testing a resumable batch requires the second.

No network, no GPU, no model. Every test in the suite that involves captioning
or profiling runs on these, in milliseconds.
"""

import hashlib
from collections.abc import Callable, Sequence

from kiseki.ports.models import (
    CaptionRequest,
    Completion,
    ModelUnavailableError,
    Usage,
)

DEFAULT_DIMENSIONS = 8
CHARACTERS_PER_TOKEN = 4
TOKENS_PER_IMAGE = 100


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARACTERS_PER_TOKEN)


class FakeImageCaptioner:
    """Captions derived from a hash of the images, so they are stable and distinct."""

    def __init__(
        self,
        describe: Callable[[CaptionRequest], str] | None = None,
        fail_on: Callable[[CaptionRequest], bool] | None = None,
        model: str = "fake-captioner",
    ) -> None:
        self._describe = describe if describe is not None else self._digest_of
        self._fail_on = fail_on if fail_on is not None else (lambda _: False)
        self._model = model
        self._usage = Usage()
        self.seen: list[CaptionRequest] = []
        """Every request made, for a test to assert against."""

    @staticmethod
    def _digest_of(request: CaptionRequest) -> str:
        digest = hashlib.sha256(b"".join(request.images)).hexdigest()[:8]
        return f"a scene ({digest})"

    def caption(self, requests: Sequence[CaptionRequest]) -> list[Completion]:
        completions = []
        for request in requests:
            self.seen.append(request)
            if self._fail_on(request):
                self._usage = self._usage.record_failure()
                raise ModelUnavailableError("the fake captioner was told to fail")

            text = self._describe(request)
            completion = Completion(
                text=text,
                model=self._model,
                input_tokens=_estimate_tokens(request.prompt)
                + len(request.images) * TOKENS_PER_IMAGE,
                output_tokens=_estimate_tokens(text),
            )
            self._usage = self._usage.record(completion)
            completions.append(completion)
        return completions

    @property
    def usage(self) -> Usage:
        return self._usage


class FakeLanguageModel:
    """Echoes the prompt unless told otherwise."""

    def __init__(
        self,
        answer: Callable[[str, str], str] | None = None,
        fail_on: Callable[[str], bool] | None = None,
        model: str = "fake-language-model",
    ) -> None:
        self._answer = (
            answer if answer is not None else (lambda system, prompt: f"echo: {prompt[:40]}")
        )
        self._fail_on = fail_on if fail_on is not None else (lambda _: False)
        self._model = model
        self._usage = Usage()
        self.seen: list[tuple[str, str]] = []
        """Every (system, prompt) pair, for a test to assert against."""

    def complete(self, system: str, prompts: Sequence[str]) -> list[Completion]:
        completions = []
        for prompt in prompts:
            self.seen.append((system, prompt))
            if self._fail_on(prompt):
                self._usage = self._usage.record_failure()
                raise ModelUnavailableError("the fake language model was told to fail")

            text = self._answer(system, prompt)
            completion = Completion(
                text=text,
                model=self._model,
                input_tokens=_estimate_tokens(system) + _estimate_tokens(prompt),
                output_tokens=_estimate_tokens(text),
            )
            self._usage = self._usage.record(completion)
            completions.append(completion)
        return completions

    @property
    def usage(self) -> Usage:
        return self._usage


class FakeTextEmbedder:
    """Vectors derived from a hash, normalised, so similarity behaves sensibly."""

    def __init__(self, dimensions: int = DEFAULT_DIMENSIONS) -> None:
        if dimensions < 1:
            raise ValueError("an embedder needs at least one dimension")
        self._dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            raw = [digest[index % len(digest)] / 255.0 for index in range(self._dimensions)]
            length = sum(value * value for value in raw) ** 0.5 or 1.0
            vectors.append(tuple(value / length for value in raw))
        return vectors

    @property
    def dimensions(self) -> int:
        return self._dimensions
