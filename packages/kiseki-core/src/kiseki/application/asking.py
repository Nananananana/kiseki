"""Asking: one question, answered from the owner's own readings.

Retrieval chooses the facts (ADR-0037); the model only phrases the
answer over a closed, numbered list and must cite what it uses -- the
narrative shape (ADR-0022). Confidence, the time range and the
evidence come from the retrieval, never from the model: the model
cannot make an answer more certain than the evidence is. With no
evidence there is no model call at all. See ADR-0038.
"""

from collections.abc import Callable, Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import datetime

from kiseki.application.grounding import Grounding, mean_confidence, numbered
from kiseki.application.retrieval import DEFAULT_LIMIT, RRF_K, Retrieval, retrieve
from kiseki.domain.insight import Insight, InsightReport
from kiseki.domain.services.time_expressions import read_time_window
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.domain.shared.moment import naive
from kiseki.ports.models import LanguageModel, TextEmbedder
from kiseki.ports.search import SearchIndex

LANGUAGE_NAMES = {"ja": "Japanese", "en": "English"}

ASK_SYSTEM = (
    "You answer one question about the person's own history, from a"
    " closed list of numbered facts. Two kinds appear. [F...] are"
    " single moments -- one photograph, one note, one page. [G...] are"
    " patterns the library derived from all of the data: places"
    " returned to, interests, trends, how often they go out."
    " Use only these facts. Prefer [G...] for questions about habits,"
    " patterns and change, and [F...] for questions about particular"
    " occasions. After each claim, cite the fact it rests on, like"
    " [F3] or [G2]. If the facts only partly answer the question, say"
    " what they do support and what they do not, rather than refusing:"
    " a partial answer that names its limits is useful and a refusal"
    " is not. Never invent a fact and never mention coordinates."
    " Answer in {language}, in one short paragraph."
)

CONFIDENCE_HALF_FACTS = 2
"""Evidence pieces at which the coverage factor reaches one half."""


def _local_now() -> datetime:
    """The owner's clock, timezone aware, so windows compare with data."""
    return datetime.now().astimezone()


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
    since: datetime | None = None
    until: datetime | None = None
    supporting_insights: tuple[Insight, ...] = ()

    grounding: tuple[Grounding, ...] = ()
    """What the library already knew, as against what was retrieved.

    Carried separately from `evidence` so a reader can see which kind
    of thing an answer rested on. An answer from patterns alone is a
    different claim from one built on three photographs, and the two
    were indistinguishable while only one of them existed."""

    @property
    def answered(self) -> bool:
        return bool(self.evidence) or bool(self.grounding)

    @property
    def grounded_only(self) -> bool:
        """No moment matched; the answer came from patterns alone."""
        return not self.evidence and bool(self.grounding)


UNSCORED_GROUNDING = 0.4
"""What patterns are worth when none of them carries a confidence.

Reached only when every offered pattern was built by a derivation that
computes none -- today, the rhythm fact from `kiseki report`, which is
a count rather than an estimate. A count is real and is not an
opinion, so this is below the middle rather than at it.

Chosen, not measured, and the docstring is where that is said. Every
other path below uses a number some derivation computed."""

PATTERN_CEILING = 0.75
"""The most an answer from patterns alone may be worth.

A pattern is a real derivation over all of the owner's data, and an
`Anchor` with twelve visits can carry a confidence of 1.0. That is
1.0 about *the anchor*, not about the question somebody asked -- the
question may have been about an occasion, and no pattern speaks to an
occasion however certain it is of a habit.

So a derived confidence is scaled into this ceiling rather than used
raw. The number is chosen; what it is chosen *about* is the gap
between "this habit is certain" and "this answers what you asked"."""


def derive_confidence(
    results: tuple[Retrieval, ...], grounding: tuple[Grounding, ...] = ()
) -> float:
    """How strongly, and how much, the answer rests on.

    Strength is 1.0 when the best document led both channels; coverage
    grows with the number of evidence pieces. The model never touches
    this number.

    With no retrieval but some grounding, it is the mean of the
    confidences the derivations already computed, scaled into
    `PATTERN_CEILING`. That replaces a flat 0.5 that this module's own
    docstring called *a floor, not a measurement* (#390): an anchor
    with twelve visits and one with two now reach an answer as
    different-sized facts, which they always were.

    With both, retrieval decides and the grounding cannot raise it: a
    pattern must not make a claim about an occasion more certain than
    the occasion's own evidence.
    """
    if not results:
        if not grounding:
            return 0.0
        derived = mean_confidence(grounding)
        if derived is None:
            return UNSCORED_GROUNDING
        return derived * PATTERN_CEILING
    strength = min(1.0, results[0].score * (RRF_K + 1) / 2)
    coverage = len(results) / (len(results) + CONFIDENCE_HALF_FACTS)
    return strength * coverage


_DOC_PREFIXES = {"caption:": "stay:", "photo:": "single:", "screen:": "screen:"}


def excluded_doc_keys(excluded: AbstractSet[str]) -> frozenset[str]:
    """The index documents an exclusion reaches (ADR-0044, part 2)."""
    keys: set[str] = set()
    for reference in excluded:
        for reference_prefix, document_prefix in _DOC_PREFIXES.items():
            if reference.startswith(reference_prefix):
                keys.add(document_prefix + reference[len(reference_prefix) :])
    return frozenset(keys)


def _supporting(
    insights: InsightReport | None,
    question: str,
    results: tuple[Retrieval, ...],
) -> tuple[Insight, ...]:
    """Findings whose topic touches the question or its evidence.

    They ride the contract as metadata for the reader; the model
    never sees them, so an answer can never borrow their certainty.
    """
    if insights is None:
        return ()
    haystack = question.lower() + " " + " ".join(item.document.text.lower() for item in results)
    matched = [item for item in insights.insights if item.topic.lower() in haystack]
    return tuple(matched[:3])


def numbered_facts(results: tuple[Retrieval, ...]) -> str:
    return "\n".join(
        f"[F{index}] ({item.document.observed_at:%Y-%m-%d}, {item.document.kind})"
        f" {item.document.text}"
        for index, item in enumerate(results, start=1)
    )


DEFAULT_REACH = Distance(30_000)


def _reachable(
    near: GeoPoint | None,
    within: Distance,
    locations: Mapping[str, GeoPoint] | None,
) -> frozenset[str] | None:
    """The doc keys within reach, or None when no place was asked."""
    if near is None:
        return None
    known = locations if locations is not None else {}
    return frozenset(
        key for key, point in known.items() if point.distance_to(near).meters <= within.meters
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
    excluded: AbstractSet[str] = frozenset(),
    near: GeoPoint | None = None,
    within: Distance = DEFAULT_REACH,
    locations: Mapping[str, GeoPoint] | None = None,
    insights: InsightReport | None = None,
    grounding: Sequence[Grounding] | None = None,
    now: Callable[[], datetime] = _local_now,
) -> Answer:
    """One answer. Model errors propagate to the caller.

    Words like "last year" in the question become the window unless
    an explicit since/until is given (ADR-0039).
    """
    if since is None and until is None:
        window = read_time_window(question, now())
        if window is not None:
            since, until = window.since, window.until
    results: tuple[Retrieval, ...] = ()
    if index.document_count() > 0:
        results = retrieve(
            index,
            embedder,
            embedding_model,
            question,
            limit=limit,
            since=since,
            until=until,
            allowed=_reachable(near, within, locations),
        )
    if near is not None:
        known = locations if locations is not None else {}
        results = tuple(
            item
            for item in results
            if item.document.doc_key in known
            and known[item.document.doc_key].distance_to(near).meters <= within.meters
        )
    banned = excluded_doc_keys(excluded)
    if banned:
        results = tuple(item for item in results if item.document.doc_key not in banned)
    patterns = tuple(grounding or ())
    if not results and not patterns:
        return Answer(question, "", 0.0, None, None, (), "", since=since, until=until)

    parts = []
    if results:
        parts.append("Moments:\n" + numbered_facts(results))
    if patterns:
        parts.append("Patterns:\n" + numbered(patterns))

    # Compared in one shape, returned in the shape it was stored in.
    #
    # Retrieval's documents carry naive moments; a grounding fact
    # carries whatever the derivation stored, which for an anchor
    # period is aware. Mixed, `min()` raises "can't compare
    # offset-naive and offset-aware datetimes" -- precisely the defect
    # ADR-0064 was written about, reached again by a path that did not
    # exist when it was written.
    #
    # The fix is the one that ADR already prescribes, and the first
    # attempt here got it half right: comparing with `naive()` and
    # then *returning* the naive value stripped the offset from
    # `first_seen`, which the API and the view print. So the key is
    # naive and the value is not.
    observed = [item.document.observed_at for item in results]
    observed += [fact.observed_at for fact in patterns if fact.observed_at is not None]

    system = ASK_SYSTEM.format(language=LANGUAGE_NAMES.get(language, "English"))
    prompt = f"Question: {question}\n\n" + "\n\n".join(parts)
    completion = language_model.complete(system, [prompt])[0]
    return Answer(
        question=question,
        answer=completion.text,
        confidence=derive_confidence(results, patterns),
        first_seen=min(observed, key=naive) if observed else None,
        last_seen=max(observed, key=naive) if observed else None,
        evidence=results,
        model=completion.model,
        since=since,
        until=until,
        supporting_insights=_supporting(insights, question, results),
        grounding=patterns,
    )
