"""Port for the search index.

The index is derived from the caption, single-caption and screen
stores; it can always be rebuilt, so it accumulates idempotently.
Query methods arrive with the retrieval work. See ADR-0036.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class SearchDocument:
    """One indexable text: where it came from, and when it happened."""

    doc_key: str
    kind: str
    text: str
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.doc_key.strip():
            raise ValueError("a search document needs a key")
        if not self.text.strip():
            raise ValueError("a search document needs text")


class SearchIndex(Protocol):
    """Keeps documents and their vectors; both accumulate idempotently."""

    def put_document(self, document: SearchDocument) -> None:
        """Add the document unless its key is already indexed."""
        ...

    def has_document(self, doc_key: str) -> bool: ...

    def document_count(self) -> int: ...

    def put_embedding(self, doc_key: str, model: str, vector: tuple[float, ...]) -> None:
        """Keep a vector for the document, replacing any for the same model."""
        ...

    def missing_embeddings(
        self, model: str, limit: int | None = None
    ) -> tuple[SearchDocument, ...]:
        """Documents without a vector for this model, oldest observed first."""
        ...

    def embedding_count(self, model: str) -> int: ...
