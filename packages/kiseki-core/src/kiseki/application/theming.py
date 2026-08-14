"""Theming: gather the labels into themes, once per label universe.

Meaning gathers, co-occurrence vouches. Labels join a cluster on
embedding similarity alone when it is high; on middling similarity
they join only when their stays overlap the cluster's -- a car that
keeps appearing where the trees and landscapes do is part of the
outdoors, a car that appears elsewhere is just a car. Names come from
the language model out of a closed member list, with a deterministic
fallback so a chatty or absent namer never stops the run. See
ADR-0023.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.caption.themes import Theme, ThemeSet, ThemeSetKey
from kiseki.ports.models import (
    LanguageModel,
    ModelRefusedError,
    ModelUnavailableError,
    TextEmbedder,
)
from kiseki.ports.subjects import SubjectRepository
from kiseki.ports.themes import ThemeSetRepository

SIMILARITY_HIGH = 0.75
"""Cosine similarity at which meaning alone joins a label to a
cluster. Calibrated against real labels; a named constant so
calibration is a one-line change."""

SIMILARITY_MID = 0.60
"""The floor for a co-occurrence-backed join. Below it, no amount of
shared stays makes two labels one theme."""

COOCCURRENCE_SHARE = 0.5
"""For a middling-similarity join, at least this share of the label's
stays must already be the cluster's. Evidence, not vibes."""

MIN_LABELS = 4
MIN_THEME_MEMBERS = 2

NAMING_SYSTEM = (
    "You name a theme from a closed list of member labels. Answer with"
    " one short lowercase English name, one or two words, as a JSON"
    " string. Use only what the members have in common; no commentary."
)

MAX_NAME_WORDS = 3


def cluster_labels(
    vectors: dict[str, tuple[float, ...]],
    stays: dict[str, frozenset[str]],
) -> tuple[tuple[str, ...], ...]:
    """Greedy and deterministic: busiest labels seed the clusters.

    Labels are processed by descending stay count (ties
    alphabetical); each joins its most similar cluster when the join
    rule allows, else starts its own. No randomness anywhere, so the
    same inputs always make the same themes.
    """
    ordered = sorted(vectors, key=lambda label: (-len(stays.get(label, frozenset())), label))
    members: list[list[str]] = []
    centroids: list[tuple[float, ...]] = []
    cluster_stays: list[set[str]] = []

    for label in ordered:
        vector = vectors[label]
        best = -1
        best_similarity = -1.0
        for index, centroid in enumerate(centroids):
            similarity = _dot(vector, centroid)
            if similarity > best_similarity:
                best_similarity = similarity
                best = index

        if best >= 0 and _joins(label, best_similarity, stays, cluster_stays[best]):
            members[best].append(label)
            cluster_stays[best] |= set(stays.get(label, frozenset()))
            centroids[best] = _mean([vectors[member] for member in members[best]])
        else:
            members.append([label])
            centroids.append(vector)
            cluster_stays.append(set(stays.get(label, frozenset())))

    return tuple(tuple(cluster) for cluster in members if len(cluster) >= MIN_THEME_MEMBERS)


def _joins(
    label: str,
    similarity: float,
    stays: dict[str, frozenset[str]],
    cluster_stays: set[str],
) -> bool:
    if similarity >= SIMILARITY_HIGH:
        return True
    if similarity < SIMILARITY_MID:
        return False
    label_stays = stays.get(label, frozenset())
    if not label_stays:
        return False
    share = len(label_stays & cluster_stays) / len(label_stays)
    return share >= COOCCURRENCE_SHARE


def parse_theme_name(answer: str) -> str | None:
    """Read one short name out of a model's answer, tolerantly.

    Accepts a JSON string, a fenced answer, or a bare word or two.
    Anything longer than a name parses to None, and the caller falls
    back to a deterministic one.
    """
    cleaned = answer.replace("```json", "").replace("```", "").strip()
    line = cleaned.splitlines()[0].strip() if cleaned else ""
    line = line.strip("\"'`[]{} ").strip()
    words = [word for word in line.lower().split() if word]
    if not words or len(words) > MAX_NAME_WORDS:
        return None
    return " ".join(words)


@dataclass(frozen=True)
class ThemeRunReport:
    """What one run did, for reporting back to whoever asked."""

    themes_made: int
    labels_considered: int
    already_done: bool
    fallback_named: int
    """Themes named deterministically because the namer's answer was
    unusable or the namer was unavailable. The run finishes either
    way; a name is decoration, the members are the substance."""


def run_theming(
    subjects: SubjectRepository,
    themes: ThemeSetRepository,
    embedder: TextEmbedder,
    language_model: LanguageModel,
    now: Callable[[], datetime] = datetime.now,
) -> ThemeRunReport:
    """Compute the theme set for the current label universe, once."""
    label_stays: dict[str, set[str]] = {}
    for reading in subjects.all():
        if not reading.answered:
            continue
        for raw in reading.labels:
            label = _normalised(raw)
            if label:
                label_stays.setdefault(label, set()).add(reading.key.value)

    labels = sorted(label_stays)
    if len(labels) < MIN_LABELS:
        return ThemeRunReport(0, len(labels), False, 0)

    key = ThemeSetKey.of(labels)
    if themes.get(key) is not None:
        return ThemeRunReport(0, len(labels), True, 0)

    rows = embedder.embed(labels)
    vectors = dict(zip(labels, rows, strict=True))
    frozen = {label: frozenset(stays) for label, stays in label_stays.items()}
    clusters = cluster_labels(vectors, frozen)

    names, model, fallback_named = _named(clusters, frozen, language_model)
    built = tuple(
        Theme(name=name, members=cluster) for name, cluster in zip(names, clusters, strict=True)
    )
    themes.save(ThemeSet(key=key, themes=built, model=model, created_at=now()))
    return ThemeRunReport(len(built), len(labels), False, fallback_named)


def _named(
    clusters: tuple[tuple[str, ...], ...],
    stays: dict[str, frozenset[str]],
    language_model: LanguageModel,
) -> tuple[list[str], str, int]:
    fallbacks = [_fallback_name(cluster, stays) for cluster in clusters]
    if not clusters:
        return [], "", 0
    prompts = ["Members: " + ", ".join(cluster) for cluster in clusters]
    try:
        completions = language_model.complete(NAMING_SYSTEM, prompts)
    except (ModelRefusedError, ModelUnavailableError):
        return fallbacks, "", len(fallbacks)

    names: list[str] = []
    fallback_named = 0
    for completion, fallback in zip(completions, fallbacks, strict=True):
        name = parse_theme_name(completion.text)
        if name is None:
            name = fallback
            fallback_named += 1
        names.append(name)
    return names, completions[0].model, fallback_named


def _fallback_name(cluster: tuple[str, ...], stays: dict[str, frozenset[str]]) -> str:
    return min(cluster, key=lambda member: (-len(stays.get(member, frozenset())), member))


def _mean(vectors: list[tuple[float, ...]]) -> tuple[float, ...]:
    dimensions = len(vectors[0])
    summed = [
        sum(vector[index] for vector in vectors) / len(vectors) for index in range(dimensions)
    ]
    length = sum(value * value for value in summed) ** 0.5 or 1.0
    return tuple(value / length for value in summed)


def _dot(one: tuple[float, ...], other: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(one, other, strict=True))


def _normalised(raw: str) -> str:
    # Keep in step with subject_interest_derivation._normalised.
    return raw.replace("_", " ").strip()
