"""Every retrieval names the channels that found it."""

from datetime import UTC, datetime

from kiseki.adapters.fake.search import FakeSearchIndex
from kiseki.application.retrieval import retrieve
from kiseki.ports.search import SearchDocument

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


class StubEmbedder:
    def embed(self, texts):
        return [(1.0, 0.0) for _ in texts]

    @property
    def dimensions(self):
        return 2


def test_a_word_match_is_named():
    index = FakeSearchIndex()
    index.put_document(SearchDocument("stay:aa", "stay", "a bowl of ramen", WHEN))
    results = retrieve(index, StubEmbedder(), "m", "ramen")
    assert results[0].channels == ("words",)


def test_both_channels_are_named():
    index = FakeSearchIndex()
    index.put_document(SearchDocument("stay:aa", "stay", "a bowl of ramen", WHEN))
    index.put_embedding("stay:aa", "m", (1.0, 0.0))
    results = retrieve(index, StubEmbedder(), "m", "ramen")
    assert results[0].channels == ("meaning", "words")
