"""Retrieval: the words and the meaning, fused deterministically.

Two channels ask the index -- FTS5 for the words, cosine over the
stored vectors for the meaning -- and reciprocal rank fusion merges
them, so a document found by both outranks one found by either alone.
The fusion is arithmetic on ranks: same index, same question, same
answer. A Japanese question meets the English captions through the
meaning channel; the words channel adds precision when the words do
match. An unavailable embedder degrades to words alone rather than
failing the question. See ADR-0037.
"""

from dataclasses import dataclass
from datetime import datetime

from kiseki.ports.models import ModelUnavailableError, TextEmbedder
from kiseki.ports.search import SearchDocument, SearchIndex

RRF_K = 60
"""The usual reciprocal-rank-fusion constant: large enough that a
first place does not drown everything below it."""

CHANNEL_DEPTH = 30
"""How deep each channel is asked before fusion."""

DEFAULT_LIMIT = 8


@dataclass(frozen=True)
class Retrieval:
    """One retrieved document and its fused score."""

    document: SearchDocument
    score: float


def retrieve(
    index: SearchIndex,
    embedder: TextEmbedder,
    embedding_model: str,
    query: str,
    limit: int = DEFAULT_LIMIT,
    since: datetime | None = None,
    until: datetime | None = None,
) -> tuple[Retrieval, ...]:
    """The best documents for the question, best first."""
    channels = [index.match_text(query, CHANNEL_DEPTH)]
    try:
        vector: tuple[float, ...] | None = embedder.embed([query])[0]
    except ModelUnavailableError:
        vector = None
    if vector is not None:
        channels.append(index.match_meaning(vector, embedding_model, CHANNEL_DEPTH))

    scores: dict[str, float] = {}
    documents: dict[str, SearchDocument] = {}
    for hits in channels:
        rank = 0
        for hit in hits:
            if not _within(hit.document, since, until):
                continue
            rank += 1
            key = hit.document.doc_key
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
            documents[key] = hit.document
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return tuple(Retrieval(documents[key], score) for key, score in ordered[:limit])


def _within(document: SearchDocument, since: datetime | None, until: datetime | None) -> bool:
    if since is not None and document.observed_at < since:
        return False
    return not (until is not None and document.observed_at > until)
