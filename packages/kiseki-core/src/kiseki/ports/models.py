"""Ports for the models.

Three things are abstracted here: something that looks at images, something that
writes prose, and something that turns text into vectors. All three are
protocols, so an implementation never imports this library.

The shape of these ports is chosen for a hosted model as much as a local one,
because a library that assumes localhost has to be rewritten the first time
somebody points it at a service. Three consequences follow: calls are batched,
failures are typed so a caller knows whether to retry, and usage is counted so a
run can be costed before it is started.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class ModelUnavailableError(RuntimeError):
    """The model could not be reached, or could not answer in time.

    A timeout, a rate limit, a service still loading a model. Retrying later is
    reasonable, and a resumable batch should treat this as a pause rather than a
    failure of the work.
    """


class ModelRefusedError(RuntimeError):
    """The model rejected the request itself.

    A malformed prompt, an image too large, content the service declines to
    process. Retrying the same request will produce the same answer, so a batch
    should record it and move on.
    """


@dataclass(frozen=True)
class CaptionRequest:
    """Ask for a description of one stop, from several of its photographs."""

    images: tuple[bytes, ...]
    prompt: str
    context: str = ""
    """Where and when, in words. Optional, and it improves the answer."""

    def __post_init__(self) -> None:
        if not self.images:
            raise ValueError("a caption request needs at least one image")
        if not self.prompt.strip():
            raise ValueError("a caption request needs a prompt")


@dataclass(frozen=True)
class Completion:
    """What a model produced, and what it cost.

    The model name travels with the text so that a caption made by one model and
    a narrative written from it by another can be told apart later. When a
    prompt changes and output has to be regenerated, this is how the stale
    entries are found.
    """

    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class Usage:
    """A running count of what has been asked of a model.

    Immutable, so that recording never mutates something a caller is holding.
    Local models cost only time; hosted ones cost money, and a run of a thousand
    captions should be costable before it starts rather than after.
    """

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    failures: int = 0

    def record(self, completion: Completion) -> "Usage":
        return Usage(
            calls=self.calls + 1,
            input_tokens=self.input_tokens + completion.input_tokens,
            output_tokens=self.output_tokens + completion.output_tokens,
            failures=self.failures,
        )

    def record_failure(self) -> "Usage":
        """A refused request still costs time, and may still cost money."""
        return Usage(
            calls=self.calls + 1,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            failures=self.failures + 1,
        )


class ImageCaptioner(Protocol):
    """Describes what is in a set of photographs."""

    def caption(self, requests: Sequence[CaptionRequest]) -> list[Completion]:
        """One completion per request, in the order given.

        Raises ModelUnavailableError if the model could not be reached, and
        ModelRefusedError if it declined the request.
        """
        ...

    @property
    def usage(self) -> Usage: ...


class LanguageModel(Protocol):
    """Writes prose from text."""

    def complete(self, system: str, prompts: Sequence[str]) -> list[Completion]:
        """One completion per prompt, in the order given."""
        ...

    @property
    def usage(self) -> Usage: ...


class TextEmbedder(Protocol):
    """Turns text into vectors for retrieval."""

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        """One vector per text, in the order given, each of `dimensions` width."""
        ...

    @property
    def dimensions(self) -> int:
        """The width of every vector this produces. A stored index depends on it."""
        ...
