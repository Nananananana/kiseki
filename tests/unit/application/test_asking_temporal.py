"""The question's own words drive the ask window (ADR-0039)."""

from datetime import UTC, datetime

from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.adapters.fake.search import FakeSearchIndex
from kiseki.application.asking import ask
from kiseki.interfaces.payloads import answer_payload
from kiseki.ports.search import SearchDocument

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
OLD = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
NEW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

KYONEN = "\u53bb\u5e74"


class StubEmbedder:
    def embed(self, texts):
        return [(1.0, 0.0) for _ in texts]

    @property
    def dimensions(self):
        return 2


def _index() -> FakeSearchIndex:
    index = FakeSearchIndex()
    index.put_document(SearchDocument("stay:aa", "stay", "a bowl of ramen", OLD))
    index.put_document(SearchDocument("stay:bb", "stay", "a bowl of ramen soup", NEW))
    return index


def _ask(question: str, **kwargs):
    return ask(
        index=_index(),
        embedder=StubEmbedder(),
        embedding_model="m",
        language_model=FakeLanguageModel(answer=lambda system, prompt: "ramen [F1]"),
        question=question,
        now=lambda: NOW,
        **kwargs,
    )


def test_the_question_carries_its_own_window():
    answer = _ask(KYONEN + " ramen ?")
    assert [item.document.doc_key for item in answer.evidence] == ["stay:aa"]
    assert answer.since is not None and answer.since.year == 2025
    assert answer.until is not None and answer.until.year == 2025


def test_an_explicit_window_beats_the_words():
    answer = _ask(
        KYONEN + " ramen ?",
        since=datetime(2026, 1, 1, tzinfo=UTC),
        until=NOW,
    )
    assert [item.document.doc_key for item in answer.evidence] == ["stay:bb"]
    assert answer.since == datetime(2026, 1, 1, tzinfo=UTC)


def test_the_window_travels_in_the_contract():
    payload = answer_payload(_ask(KYONEN + " ramen ?"))
    assert payload["since"] is not None and payload["since"].startswith("2025")
    assert payload["until"] is not None and payload["until"].startswith("2025")
