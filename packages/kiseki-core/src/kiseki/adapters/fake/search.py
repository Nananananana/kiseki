"""In-memory search index, for tests and examples."""

from __future__ import annotations

import re

from kiseki.ports.search import SearchDocument, SearchHit


class FakeSearchIndex:
    """Keeps documents and vectors in memory; conforms to SearchIndex."""

    def __init__(self) -> None:
        self._documents: dict[str, SearchDocument] = {}
        self._embeddings: dict[tuple[str, str], tuple[float, ...]] = {}

    def put_document(self, document: SearchDocument) -> None:
        if document.doc_key not in self._documents:
            self._documents[document.doc_key] = document

    def has_document(self, doc_key: str) -> bool:
        return doc_key in self._documents

    def document_count(self) -> int:
        return len(self._documents)

    def put_embedding(self, doc_key: str, model: str, vector: tuple[float, ...]) -> None:
        self._embeddings[(doc_key, model)] = vector

    def missing_embeddings(
        self, model: str, limit: int | None = None
    ) -> tuple[SearchDocument, ...]:
        pending = sorted(
            (
                document
                for document in self._documents.values()
                if (document.doc_key, model) not in self._embeddings
            ),
            key=lambda document: (document.observed_at, document.doc_key),
        )
        return tuple(pending if limit is None else pending[:limit])

    def embedding_count(self, model: str) -> int:
        return sum(1 for _key, kept in self._embeddings if kept == model)

    def match_text(self, query: str, limit: int) -> tuple[SearchHit, ...]:
        tokens = re.findall(r"\w+", query.lower())
        if not tokens:
            return ()
        scored: list[tuple[float, str]] = []
        for document in self._documents.values():
            text = document.text.lower()
            score = float(sum(text.count(token) for token in tokens))
            if score > 0:
                scored.append((-score, document.doc_key))
        scored.sort()
        return tuple(
            SearchHit(self._documents[doc_key], -negative) for negative, doc_key in scored[:limit]
        )

    def match_meaning(
        self, query_vector: tuple[float, ...], model: str, limit: int
    ) -> tuple[SearchHit, ...]:
        scored: list[tuple[float, str]] = []
        for (doc_key, kept), vector in self._embeddings.items():
            if kept != model or len(vector) != len(query_vector):
                continue
            if doc_key not in self._documents:
                continue
            score = sum(a * b for a, b in zip(vector, query_vector, strict=True))
            scored.append((-score, doc_key))
        scored.sort()
        return tuple(
            SearchHit(self._documents[doc_key], -negative) for negative, doc_key in scored[:limit]
        )
