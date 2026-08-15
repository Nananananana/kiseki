"""Indexing: every answered reading becomes one searchable document.

The documents are derived and deterministic -- syncing them costs
nothing and repeats safely. The vectors cost model time, so they are
the resumable part: the embeddings table doubles as the progress
record and an unavailable model pauses the run (ADR-0015). A refusal
propagates, because for an embedder it means configuration, not
weather -- the shape of the theming run. Withheld photographs
(ADR-0032) are never indexed, sensitive screen readings carry no
labels and so nothing to index, and no coordinate ever enters a
document. See ADR-0036.
"""

from dataclasses import dataclass

from kiseki.ports.captions import CaptionRepository
from kiseki.ports.models import ModelUnavailableError, TextEmbedder
from kiseki.ports.repositories import PhotoRepository
from kiseki.ports.screens import ScreenshotReadingRepository
from kiseki.ports.search import SearchDocument, SearchIndex
from kiseki.ports.singles import SingleCaptionRepository

EMBED_CHUNK = 32
"""Vectors are saved chunk by chunk, so a pause loses at most one
chunk of model time. Matches the transport chunking of the Ollama
embed adapter."""


@dataclass(frozen=True)
class IndexRunReport:
    """What one run did, for reporting back to whoever asked."""

    documents_added: int
    documents_total: int
    embedded: int
    already_embedded: int
    paused: bool
    """True when the model became unavailable and the run stopped early.
    Running again continues from where it paused."""


def gather_documents(
    photos: PhotoRepository,
    captions: CaptionRepository,
    singles: SingleCaptionRepository,
    screens: ScreenshotReadingRepository,
) -> tuple[SearchDocument, ...]:
    """Every indexable reading, deterministically. No model, no coordinate."""
    observations = photos.all()
    captured = {item.photo_id: item.captured_at for item in observations}
    withheld = {item.photo_id for item in observations if not item.may_inform_preferences}

    documents: list[SearchDocument] = []
    for caption in captions.all():
        if not caption.answered:
            continue
        times = [captured[pid] for pid in caption.photo_ids if pid in captured]
        if not times:
            continue
        documents.append(
            SearchDocument(f"stay:{caption.key.value}", "stay", caption.text, min(times))
        )
    for single in singles.all():
        if not single.answered:
            continue
        if single.photo_id in withheld or single.photo_id not in captured:
            continue
        documents.append(
            SearchDocument(
                f"single:{single.photo_id.value}",
                "single",
                single.text,
                captured[single.photo_id],
            )
        )
    for reading in screens.all():
        if reading.refused is not None or not reading.labels:
            continue
        if reading.photo_id in withheld or reading.photo_id not in captured:
            continue
        documents.append(
            SearchDocument(
                f"screen:{reading.photo_id.value}",
                "screen",
                f"{reading.category}: {', '.join(reading.labels)}",
                captured[reading.photo_id],
            )
        )
    return tuple(documents)


def run_indexing(
    photos: PhotoRepository,
    captions: CaptionRepository,
    singles: SingleCaptionRepository,
    screens: ScreenshotReadingRepository,
    index: SearchIndex,
    embedder: TextEmbedder,
    embedding_model: str,
    limit: int | None = None,
) -> IndexRunReport:
    """Sync the documents, then embed what lacks a vector, oldest first."""
    added = 0
    for document in gather_documents(photos, captions, singles, screens):
        if not index.has_document(document.doc_key):
            index.put_document(document)
            added += 1

    already = index.embedding_count(embedding_model)
    pending = index.missing_embeddings(embedding_model, limit)
    embedded = 0
    paused = False
    for start in range(0, len(pending), EMBED_CHUNK):
        chunk = pending[start : start + EMBED_CHUNK]
        try:
            vectors = embedder.embed([document.text for document in chunk])
        except ModelUnavailableError:
            paused = True
            break
        for document, vector in zip(chunk, vectors, strict=True):
            index.put_embedding(document.doc_key, embedding_model, vector)
            embedded += 1

    return IndexRunReport(added, index.document_count(), embedded, already, paused)
