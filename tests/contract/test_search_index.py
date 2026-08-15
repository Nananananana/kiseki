"""Both search indexes honour the same contract."""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.adapters.fake.search import FakeSearchIndex
from kiseki.adapters.sqlite.search import SqliteSearchIndex
from kiseki.adapters.sqlite.store import connect
from kiseki.ports.search import SearchDocument

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _document(key: str = "stay:aa", minutes: int = 0) -> SearchDocument:
    return SearchDocument(key, "stay", "a bowl of ramen", WHEN + timedelta(minutes=minutes))


@pytest.fixture(params=["fake", "sqlite"])
def index(request, tmp_path):
    if request.param == "fake":
        return FakeSearchIndex()
    connection = connect(tmp_path / "kiseki.sqlite3")
    request.addfinalizer(connection.close)
    return SqliteSearchIndex(connection)


def test_an_empty_index_has_nothing(index):
    assert not index.has_document("stay:aa")
    assert index.document_count() == 0
    assert index.missing_embeddings("m") == ()


def test_a_put_document_is_found(index):
    index.put_document(_document())
    assert index.has_document("stay:aa")
    assert index.document_count() == 1


def test_putting_the_same_key_again_changes_nothing(index):
    index.put_document(_document())
    index.put_document(_document())
    assert index.document_count() == 1


def test_missing_embeddings_come_oldest_first(index):
    newer = _document("single:bb", minutes=5)
    older = _document("stay:aa")
    index.put_document(newer)
    index.put_document(older)
    assert index.missing_embeddings("m") == (older, newer)


def test_an_embedding_settles_a_document(index):
    index.put_document(_document())
    index.put_embedding("stay:aa", "m", (1.0, 0.0))
    assert index.missing_embeddings("m") == ()
    assert index.embedding_count("m") == 1
    assert len(index.missing_embeddings("other")) == 1


def test_the_limit_bounds_missing_embeddings(index):
    index.put_document(_document("stay:aa"))
    index.put_document(_document("single:bb", minutes=1))
    assert len(index.missing_embeddings("m", limit=1)) == 1
