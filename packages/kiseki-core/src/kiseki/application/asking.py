"""Asking: one question, answered from the owner's own readings.

Retrieval chooses the facts (ADR-0037); the model only phrases the
answer over a closed, numbered list and must cite what it uses -- the
narrative shape (ADR-0022). Confidence, the time range and the
evidence come from the retrieval, never from the model: the model
cannot make an answer more certain than the evidence is. With no
evidence there is no model call at all. See ADR-0038.
"""

from dataclasses import dataclass
from datetime import datetime

from kiseki.application.retrieval import DEFAULT_LIMIT, RRF_K, Retrieval, retrieve
from kiseki.ports.models import LanguageModel, TextEmbedder
from kiseki.ports.search import SearchIndex

LANGUAGE_NAMES = {"ja": "Japanese", "en": "English"}

ASK_SYSTEM = (
    "You answer one question about the person's own photo history,"
    " from a closed list of numbered facts. Use only these facts; if"
    " they do not answer the question, say so briefly. After each"
    " claim, cite the fact it rests on, like [F3]. Never mention any"
    " coordinates. Answer in {language}, in one short paragraph."
)

CONFIDENCE_HALF_FACTS = 2
"""Evidence pieces at which the coverage factor reaches one half."""


@dataclass(frozen=True)
class Answer:
    """One answer and everything needed to check it."""

    question: str
    answer: str
    confidence: float
    first_seen: datetime | None
    last_seen: datetime | None
    evidence: tuple[Retrieval, ...]
    model: str

    @property
    def answered(self) -> bool:
        return bool(self.evidence)


def derive_confidence(results: tuple[Retrieval, ...]) -> float:
    """From the retrieval alone: how strongly, and how much, it found.

    Strength is 1.0 when the best document led both channels; coverage
    grows with the number of evidence pieces. The model never touches
    this number.
    """
    if not results:
        return 0.0
    strength = min(1.0, results[0].score * (RRF_K + 1) / 2)
    coverage = len(results) / (len(results) + CONFIDENCE_HALF_FACTS)
    return strength * coverage


def numbered_facts(results: tuple[Retrieval, ...]) -> str:
    return "\n".join(
        f"[F{index}] ({item.document.observed_at:%Y-%m-%d}, {item.document.kind})"
        f" {item.document.text}"
        for index, item in enumerate(results, start=1)
    )


def ask(
    index: SearchIndex,
    embedder: TextEmbedder,
    embedding_model: str,
    language_model: LanguageModel,
    question: str,
    language: str = "ja",
    limit: int = DEFAULT_LIMIT,
    since: datetime | None = None,
    until: datetime | None = None,
) -> Answer:
    """One answer. Model errors propagate to the caller."""
    results: tuple[Retrieval, ...] = ()
    if index.document_count() > 0:
        results = retrieve(
            index, embedder, embedding_model, question, limit=limit, since=since, until=until
        )
    if not results:
        return Answer(question, "", 0.0, None, None, (), "")

    observed = [item.document.observed_at for item in results]
    system = ASK_SYSTEM.format(language=LANGUAGE_NAMES.get(language, "English"))
    prompt = f"Question: {question}\n\nFacts:\n{numbered_facts(results)}"
    completion = language_model.complete(system, [prompt])[0]
    return Answer(
        question=question,
        answer=completion.text,
        confidence=derive_confidence(results),
        first_seen=min(observed),
        last_seen=max(observed),
        evidence=results,
        model=completion.model,
    )
