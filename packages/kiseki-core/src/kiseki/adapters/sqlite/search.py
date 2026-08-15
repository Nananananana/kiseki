"""SQLite search index: FTS5 for words, packed vectors for meaning.

Created by this adapter rather than by connect(), so the rest of the
library never depends on the SQLite build carrying FTS5; only search
touches it. Vectors are packed floats -- a few thousand rows brute
forced in Python are fast enough, and no dependency buys more. See
ADR-0036.
"""

from __future__ import annotations

import sqlite3
import struct
from collections.abc import Callable
from datetime import datetime

from kiseki.ports.search import SearchDocument

INDEX_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS search_documents USING fts5(
    text,
    doc_key UNINDEXED,
    kind UNINDEXED,
    observed_at UNINDEXED
);

CREATE TABLE IF NOT EXISTS search_embeddings (
    doc_key    TEXT NOT NULL,
    model      TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    vector     BLOB NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (doc_key, model)
);
"""


def pack_vector(vector: tuple[float, ...]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def unpack_vector(blob: bytes, dimensions: int) -> tuple[float, ...]:
    return struct.unpack(f"<{dimensions}f", blob)


class SqliteSearchIndex:
    """Conforms to SearchIndex; creates its own tables on first use."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._connection = connection
        self._now = now
        connection.executescript(INDEX_SCHEMA)
        connection.commit()

    def put_document(self, document: SearchDocument) -> None:
        if self.has_document(document.doc_key):
            return
        with self._connection:
            self._connection.execute(
                "INSERT INTO search_documents (text, doc_key, kind, observed_at)"
                " VALUES (?, ?, ?, ?)",
                (
                    document.text,
                    document.doc_key,
                    document.kind,
                    document.observed_at.isoformat(),
                ),
            )

    def has_document(self, doc_key: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM search_documents WHERE doc_key = ? LIMIT 1", (doc_key,)
        ).fetchone()
        return row is not None

    def document_count(self) -> int:
        total: int = self._connection.execute("SELECT COUNT(*) FROM search_documents").fetchone()[0]
        return total

    def put_embedding(self, doc_key: str, model: str, vector: tuple[float, ...]) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO search_embeddings"
                " (doc_key, model, dimensions, vector, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (doc_key, model, len(vector), pack_vector(vector), self._now().isoformat()),
            )

    def missing_embeddings(
        self, model: str, limit: int | None = None
    ) -> tuple[SearchDocument, ...]:
        sql = (
            "SELECT d.doc_key, d.kind, d.text, d.observed_at FROM search_documents d"
            " LEFT JOIN search_embeddings e ON e.doc_key = d.doc_key AND e.model = ?"
            " WHERE e.doc_key IS NULL ORDER BY d.observed_at, d.doc_key"
        )
        parameters: tuple[object, ...] = (model,)
        if limit is not None:
            sql += " LIMIT ?"
            parameters = (model, limit)
        rows = self._connection.execute(sql, parameters).fetchall()
        return tuple(
            SearchDocument(doc_key, kind, text, datetime.fromisoformat(observed_at))
            for doc_key, kind, text, observed_at in rows
        )

    def embedding_count(self, model: str) -> int:
        total: int = self._connection.execute(
            "SELECT COUNT(*) FROM search_embeddings WHERE model = ?", (model,)
        ).fetchone()[0]
        return total
