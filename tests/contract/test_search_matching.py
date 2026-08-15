"""Both search indexes answer word and meaning queries the same way."""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.adapters.fake.search import FakeSearchIndex
from kiseki.adapters.sqlite.search import SqliteSearchIndex
from kiseki.adapters.sqlite.store import connect
from kiseki.ports.search import SearchDocument, SearchHit

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _document(key: str, text: str, minutes: int = 0) -> SearchDocument:
    return SearchDocument(key, "stay", text, WHEN + timedelta(minutes=minutes))


@pytest.fixture(params=["fake", "sqlite"])
def index(request, tmp_path):
    if request.param == "fake":
        return FakeSearchIndex()
    connection = connect(tmp_path / "kiseki.sqlite3")
    request.addfinalizer(connection.close)
    return SqliteSearchIndex(connection)


def test_match_text_finds_the_word(index):
    index.put_document(_document("stay:aa", "a bowl of ramen"))
    index.put_document(_document("stay:bb", "a stone temple gate", 1))
    hits = index.match_text("ramen", 5)
    assert [hit.document.doc_key for hit in hits] == ["stay:aa"]
    assert isinstance(hits[0], SearchHit)


def test_match_text_ranks_the_denser_text_first(index):
    index.put_document(_document("stay:aa", "ramen with beans"))
    index.put_document(_document("stay:bb", "ramen ramen ramen", 1))
    hits = index.match_text("ramen", 5)
    assert [hit.document.doc_key for hit in hits] == ["stay:bb", "stay:aa"]


def test_match_text_without_words_is_empty(index):
    index.put_document(_document("stay:aa", "a bowl of ramen"))
    assert index.match_text("!!!", 5) == ()


def test_match_text_misses_politely(index):
    index.put_document(_document("stay:aa", "a bowl of ramen"))
    assert index.match_text("sushi", 5) == ()


def test_match_meaning_answers_nearest_first(index):
    index.put_document(_document("stay:aa", "a bowl of ramen"))
    index.put_document(_document("stay:bb", "a stone temple gate", 1))
    index.put_embedding("stay:aa", "m", (1.0, 0.0))
    index.put_embedding("stay:bb", "m", (0.0, 1.0))
    hits = index.match_meaning((1.0, 0.0), "m", 5)
    assert [hit.document.doc_key for hit in hits] == ["stay:aa", "stay:bb"]
    assert hits[0].score > hits[1].score


def test_match_meaning_respects_the_model(index):
    index.put_document(_document("stay:aa", "a bowl of ramen"))
    index.put_embedding("stay:aa", "m", (1.0, 0.0))
    assert index.match_meaning((1.0, 0.0), "other", 5) == ()


def test_match_meaning_honours_the_limit(index):
    index.put_document(_document("stay:aa", "a bowl of ramen"))
    index.put_document(_document("stay:bb", "a stone temple gate", 1))
    index.put_embedding("stay:aa", "m", (1.0, 0.0))
    index.put_embedding("stay:bb", "m", (0.0, 1.0))
    hits = index.match_meaning((1.0, 0.0), "m", 1)
    assert [hit.document.doc_key for hit in hits] == ["stay:aa"]
