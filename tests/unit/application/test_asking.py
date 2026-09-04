"""Asking: retrieval chooses the facts, the model only phrases them."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest
from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.adapters.fake.search import FakeSearchIndex
from kiseki.application.asking import (
    PATTERN_CEILING,
    UNSCORED_GROUNDING,
    ask,
    derive_confidence,
)
from kiseki.application.grounding import Grounding
from kiseki.ports.models import Completion, ModelRefusedError, Usage
from kiseki.ports.search import SearchDocument

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _document(key: str, text: str, minutes: int = 0) -> SearchDocument:
    return SearchDocument(key, "stay", text, WHEN + timedelta(minutes=minutes))


class StubEmbedder:
    def __init__(self, vector=(1.0, 0.0)):
        self._vector = tuple(vector)

    def embed(self, texts):
        return [self._vector for _ in texts]

    @property
    def dimensions(self):
        return len(self._vector)


class RefusingLanguageModel:
    def complete(self, system: str, prompts: Sequence[str]) -> list[Completion]:
        raise ModelRefusedError("content declined")

    @property
    def usage(self) -> Usage:
        return Usage()


def _index() -> FakeSearchIndex:
    index = FakeSearchIndex()
    index.put_document(_document("stay:aa", "a bowl of ramen"))
    index.put_document(_document("stay:bb", "a stone temple gate", 10))
    index.put_embedding("stay:aa", "m", (1.0, 0.0))
    index.put_embedding("stay:bb", "m", (0.0, 1.0))
    return index


def _ask(index=None, embedder=None, language_model=None, **kwargs):
    return ask(
        index=index if index is not None else _index(),
        embedder=embedder if embedder is not None else StubEmbedder((1.0, 0.0)),
        embedding_model="m",
        language_model=(
            language_model
            if language_model is not None
            else FakeLanguageModel(answer=lambda system, prompt: "ramen days [F1]")
        ),
        question=kwargs.pop("question", "ramen"),
        **kwargs,
    )


def test_the_model_sees_only_numbered_facts():
    model = FakeLanguageModel(answer=lambda system, prompt: "ramen days [F1]")
    answer = _ask(language_model=model)
    system, prompt = model.seen[0]
    assert "Japanese" in system
    assert "[F1]" in prompt
    assert "a bowl of ramen" in prompt
    assert "ramen" in prompt
    assert answer.answer == "ramen days [F1]"
    assert answer.model == "fake-language-model"


def test_confidence_comes_from_the_retrieval():
    answer = _ask()
    assert answer.confidence == pytest.approx(0.5)


def test_words_alone_earn_half_strength():
    index = FakeSearchIndex()
    index.put_document(_document("stay:aa", "a bowl of ramen"))
    answer = _ask(index=index)
    assert answer.confidence == pytest.approx((1 / 2) * (1 / 3))


def test_no_evidence_asks_no_model():
    model = FakeLanguageModel(answer=lambda system, prompt: "never")
    answer = _ask(index=FakeSearchIndex(), language_model=model)
    assert not answer.answered
    assert answer.confidence == 0.0
    assert answer.evidence == ()
    assert model.seen == []


def test_the_window_reaches_the_retrieval():
    answer = _ask(until=WHEN - timedelta(minutes=1))
    assert not answer.answered


def test_the_time_range_spans_the_evidence():
    answer = _ask()
    assert answer.first_seen == WHEN
    assert answer.last_seen == WHEN + timedelta(minutes=10)


def test_english_is_asked_for_in_english():
    model = FakeLanguageModel(answer=lambda system, prompt: "ramen [F1]")
    _ask(language_model=model, language="en")
    system, _prompt = model.seen[0]
    assert "English" in system


def test_model_errors_propagate():
    with pytest.raises(ModelRefusedError):
        _ask(language_model=RefusingLanguageModel())


class TestConfidenceFromPatternsAlone:
    """#390: a flat 0.5 replaced by what the derivations computed.

    The docstring on the constant it replaced called it *a floor, not
    a measurement*, which was honest and was a placeholder. An anchor
    with twelve visits and one with two now reach an answer as
    different-sized facts, which they always were.
    """

    def a_pattern(self, confidence: float | None) -> Grounding:
        return Grounding(
            kind="place",
            text="Place 1: returned to on some days.",
            source="kiseki places",
            confidence=confidence,
        )

    def test_a_strong_pattern_is_worth_more_than_a_weak_one(self) -> None:
        strong = derive_confidence((), (self.a_pattern(0.95),))
        weak = derive_confidence((), (self.a_pattern(0.20),))
        assert strong > weak, "the two patterns produced the same confidence"

    def test_it_never_reaches_certainty(self) -> None:
        """1.0 about an anchor is not 1.0 about the question somebody
        asked: no pattern speaks to an occasion, however certain it is
        of a habit."""
        assert derive_confidence((), (self.a_pattern(1.0),)) <= PATTERN_CEILING

    def test_unscored_patterns_fall_back_and_say_so(self) -> None:
        assert derive_confidence((), (self.a_pattern(None),)) == UNSCORED_GROUNDING

    def test_nothing_at_all_is_zero(self) -> None:
        assert derive_confidence((), ()) == 0.0

    def test_retrieval_decides_when_it_found_anything(self) -> None:
        """A pattern must not make a claim about an occasion more
        certain than the occasion's own evidence."""
        with_patterns = derive_confidence(_evidence(2), (self.a_pattern(1.0),))
        without = derive_confidence(_evidence(2), ())
        assert with_patterns == without


def _evidence(count: int) -> tuple:  # type: ignore[type-arg]
    """Retrievals strong enough that retrieval decides."""
    from kiseki.application.retrieval import Retrieval

    return tuple(
        Retrieval(
            SearchDocument(f"stay:{index}", "stay", "a bowl of ramen", WHEN),
            1.0 / (index + 1),
            ("words",),
        )
        for index in range(count)
    )
