"""Structural and semantic checks for kiseki-interest-export documents.

The export is the only document KISEKI prepares for the world outside
the machine (ADR-0047), which makes it the one contract other people
read. Structural rules come from the JSON Schema. The rest are here,
and they exist because a schema cannot express them: JSON Schema
2020-12 cannot compare two properties of the same object, cannot say
that a list is ordered, and cannot say that one part of a document
must agree with another.
"""

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from kiseki_conformance import schema

SCHEMA_RESOURCE = "interest-export-v1.json"

PLACE_PREFIX = "place:"


def load_export_schema() -> dict[str, Any]:
    """Return the bundled kiseki-interest-export v1 schema."""
    return schema.load(SCHEMA_RESOURCE)


def validate_export(document: object) -> list[str]:
    """Return schema violations as readable messages. Empty means valid."""
    return schema.violations(SCHEMA_RESOURCE, document)


def check_export_semantics(document: Mapping[str, Any]) -> list[str]:
    """Return violations of rules the schema cannot express."""
    messages: list[str] = []

    interests = document.get("interests")
    if not isinstance(interests, Sequence) or isinstance(interests, str):
        return ["<root>: interests must be a list"]

    messages.extend(_check_exported_on(document))

    seen: dict[str, int] = {}
    for index, interest in enumerate(interests):
        if not isinstance(interest, Mapping):
            messages.append(f"interests/{index}: an interest must be an object")
            continue
        messages.extend(_check_topic(interest, index, seen))
        messages.extend(_check_months(interest, index))

    messages.extend(_check_order(interests))
    messages.extend(_check_stages(document, set(seen)))
    return messages


def _check_exported_on(document: Mapping[str, Any]) -> list[str]:
    raw = document.get("exported_on")
    if not isinstance(raw, str):
        return []
    try:
        date.fromisoformat(raw)
    except ValueError:
        return [f"<root>: exported_on {raw!r} is not a day that happened"]
    return []


def _check_topic(interest: Mapping[str, Any], index: int, seen: dict[str, int]) -> list[str]:
    topic = interest.get("topic")
    if not isinstance(topic, str):
        return []
    messages: list[str] = []
    if topic.startswith(PLACE_PREFIX):
        messages.append(
            f"interests/{index}: topic {topic!r} names a place. A list of places is a "
            "movement history, and never leaves (ADR-0047)."
        )
    if topic in seen:
        messages.append(
            f"interests/{index}: duplicate topic {topic!r}, already given by interest "
            f"{seen[topic]}. One reading of a topic, or a consumer must decide which to believe."
        )
    else:
        seen[topic] = index
    return messages


def _month(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        year, month = value.split("-")
        return date(int(year), int(month), 1)
    except (ValueError, TypeError):
        return None


def _check_months(interest: Mapping[str, Any], index: int) -> list[str]:
    messages: list[str] = []
    months: dict[str, date] = {}
    for field in ("first_seen", "last_seen"):
        raw = interest.get(field)
        if raw is None:
            continue
        parsed = _month(raw)
        if parsed is None:
            messages.append(f"interests/{index}: {field} {raw!r} is not a month (YYYY-MM)")
        else:
            months[field] = parsed
    if len(months) == 2 and months["last_seen"] < months["first_seen"]:
        messages.append(
            f"interests/{index}: last_seen {interest['last_seen']!r} is before first_seen "
            f"{interest['first_seen']!r}. A schema cannot compare two fields; this does."
        )
    return messages


def _strength(interest: Mapping[str, Any]) -> float | None:
    score = interest.get("score")
    confidence = interest.get("confidence")
    if isinstance(score, bool) or isinstance(confidence, bool):
        return None
    if not isinstance(score, int | float) or not isinstance(confidence, int | float):
        return None
    return float(score) * float(confidence)


def _check_order(interests: Sequence[Any]) -> list[str]:
    """The document is ordered, and a consumer showing the first few
    must be shown the best few."""
    ranked: list[tuple[float, str]] = []
    for interest in interests:
        if not isinstance(interest, Mapping):
            return []
        topic = interest.get("topic")
        strength = _strength(interest)
        if not isinstance(topic, str) or strength is None:
            return []
        ranked.append((strength, topic))

    expected = [topic for _, topic in sorted(ranked, key=lambda pair: (-pair[0], pair[1]))]
    actual = [topic for _, topic in ranked]
    if expected == actual:
        return []
    first = next(index for index, topic in enumerate(actual) if topic != expected[index])
    return [
        (
            f"interests/{first}: interests are out of order. They are strongest first, by score "
            f"times confidence, and {expected[first]!r} belongs before {actual[first]!r}."
        )
    ]


def _check_stages(document: Mapping[str, Any], topics: set[str]) -> list[str]:
    stages = document.get("stages")
    if not isinstance(stages, Sequence) or isinstance(stages, str):
        return []
    messages: list[str] = []
    seen: dict[str, int] = {}
    for index, stage in enumerate(stages):
        if not isinstance(stage, Mapping):
            messages.append(f"stages/{index}: a stage must be an object")
            continue
        topic = stage.get("topic")
        if not isinstance(topic, str):
            continue
        if topic not in topics:
            messages.append(
                f"stages/{index}: a stage for {topic!r}, which is not among the interests. "
                "The two halves of the document may not disagree (ADR-0069)."
            )
        if topic in seen:
            messages.append(
                f"stages/{index}: duplicate topic {topic!r}, already staged by stage "
                f"{seen[topic]}. A topic is at one stage of its life."
            )
        else:
            seen[topic] = index
    return messages
