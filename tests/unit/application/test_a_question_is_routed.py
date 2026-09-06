"""`ask` narrows what it offers to the kinds the question is about.

Never widens: a question that routes to nothing is offered everything,
which is what every question got before ADR-0090. And a question routed
to a kind this library holds nothing for is told so by name, which is
the honest form of *fits none*.
"""

from datetime import UTC, datetime

from kiseki.adapters.fake.models import FakeLanguageModel, FakeTextEmbedder
from kiseki.application.asking import ask
from kiseki.application.grounding import Grounding
from kiseki.domain.services.question_routing import RHYTHM, TREND

WHEN = datetime(2026, 9, 1, tzinfo=UTC)


class _EmptyIndex:
    def document_count(self) -> int:
        return 0

    def search(self, *args: object, **kwargs: object) -> tuple[()]:
        return ()

    def search_embeddings(self, *args: object, **kwargs: object) -> tuple[()]:
        return ()


def _facts() -> list[Grounding]:
    return [
        Grounding(kind="place", text="a place, twelve days", source="kiseki places"),
        Grounding(kind="rhythm", text="19 outings", source="kiseki report"),
        Grounding(kind="interest", text="ramen, 0.8", source="kiseki profile"),
    ]


def _ask(question: str, facts: list[Grounding] | None = None):
    return ask(
        index=_EmptyIndex(),  # type: ignore[arg-type]
        embedder=FakeTextEmbedder(),
        embedding_model="fake",
        language_model=FakeLanguageModel(answer=lambda system, prompt: "an answer"),
        question=question,
        grounding=_facts() if facts is None else facts,
        now=lambda: WHEN,
    )


def test_a_routed_question_is_offered_only_what_it_is_about() -> None:
    answer = _ask("how often do I go out?")
    assert {fact.kind for fact in answer.grounding} == {"rhythm"}
    assert RHYTHM in answer.route.kinds


def test_an_unrouted_question_is_offered_everything() -> None:
    """Exactly what every question got before routing existed."""
    answer = _ask("what did I eat in Seoul?")
    assert not answer.route.routed
    assert {fact.kind for fact in answer.grounding} == {"place", "rhythm", "interest"}


def test_narrowing_never_empties_what_was_offered() -> None:
    """A question routed to trend, on a library holding no trend fact:
    the other facts stay rather than the answer losing everything. The
    reader is told about the trend separately."""
    answer = _ask("has this changed lately?")
    assert TREND in answer.route.kinds
    assert answer.grounding, "narrowing emptied the offer"


def test_a_kind_with_nothing_derived_is_named() -> None:
    answer = _ask("has this changed lately?")
    assert "trend" in answer.unanswerable


def test_a_kind_that_is_held_is_not_called_unanswerable() -> None:
    answer = _ask("how often do I go out?")
    assert answer.unanswerable == ()
