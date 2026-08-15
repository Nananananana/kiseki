"""In-memory search index, for tests and examples."""

from __future__ import annotations

from kiseki.ports.search import SearchDocument


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
