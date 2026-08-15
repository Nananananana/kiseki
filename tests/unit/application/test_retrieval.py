"""Hybrid retrieval: two channels, one deterministic fusion."""

from datetime import UTC, datetime, timedelta

from kiseki.adapters.fake.search import FakeSearchIndex
from kiseki.application.retrieval import retrieve
from kiseki.ports.models import ModelUnavailableError
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


class UnavailableEmbedder:
    def embed(self, texts):
        raise ModelUnavailableError("away")

    @property
    def dimensions(self):
        return 2


def _index() -> FakeSearchIndex:
    index = FakeSearchIndex()
    index.put_document(_document("stay:aa", "a bowl of ramen"))
    index.put_document(_document("stay:bb", "a stone temple gate", 10))
    index.put_embedding("stay:aa", "m", (1.0, 0.0))
    index.put_embedding("stay:bb", "m", (0.0, 1.0))
    return index


def test_a_document_found_by_both_channels_ranks_first():
    results = retrieve(_index(), StubEmbedder((1.0, 0.0)), "m", "ramen")
    assert results[0].document.doc_key == "stay:aa"
    assert len(results) == 2


def test_words_alone_answer_when_the_embedder_is_away():
    results = retrieve(_index(), UnavailableEmbedder(), "m", "ramen")
    assert [item.document.doc_key for item in results] == ["stay:aa"]


def test_the_window_filters_hits():
    results = retrieve(_index(), StubEmbedder(), "m", "ramen", since=WHEN + timedelta(minutes=5))
    assert all(item.document.doc_key != "stay:aa" for item in results)


def test_the_limit_bounds_the_answer():
    results = retrieve(_index(), StubEmbedder(), "m", "ramen", limit=1)
    assert len(results) == 1


def test_an_empty_index_answers_empty():
    assert retrieve(FakeSearchIndex(), StubEmbedder(), "m", "ramen") == ()


def test_ties_break_deterministically():
    index = FakeSearchIndex()
    index.put_document(_document("stay:aa", "a stone temple gate"))
    index.put_document(_document("stay:bb", "a wooden shrine gate", 1))
    index.put_embedding("stay:aa", "m", (1.0, 0.0))
    index.put_embedding("stay:bb", "m", (1.0, 0.0))
    first = retrieve(index, StubEmbedder((1.0, 0.0)), "m", "zzz")
    second = retrieve(index, StubEmbedder((1.0, 0.0)), "m", "zzz")
    assert first == second
    assert first[0].document.doc_key == "stay:aa"


def test_scores_come_ordered_and_positive():
    results = retrieve(_index(), StubEmbedder((1.0, 0.0)), "m", "ramen")
    scores = [item.score for item in results]
    assert scores == sorted(scores, reverse=True)
    assert all(score > 0 for score in scores)
