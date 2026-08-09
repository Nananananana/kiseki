"""Structural and semantic checks for PhotoRecord documents.

Structural checks are delegated to the JSON Schema. Semantic checks cover the
rules a schema cannot express: uniqueness, parseability, and internal
consistency across records.
"""

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from functools import lru_cache
from importlib.resources import files
from typing import Any

SCHEMA_RESOURCE = "photo-record-v1.json"


def load_schema() -> dict[str, Any]:
    """Return the bundled PhotoRecord v1 schema."""
    resource = files("kiseki_conformance").joinpath("schemas", SCHEMA_RESOURCE)
    schema: dict[str, Any] = json.loads(resource.read_text(encoding="utf-8"))
    return schema


@lru_cache(maxsize=1)
def _validator() -> Any:
    from jsonschema import Draft202012Validator

    return Draft202012Validator(load_schema())


def validate_document(document: object) -> list[str]:
    """Return schema violations as readable messages. Empty means valid."""
    messages: list[str] = []
    for error in _validator().iter_errors(document):
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        messages.append(f"{location}: {error.message}")
    return sorted(messages)


def check_semantics(document: Mapping[str, Any]) -> list[str]:
    """Return violations of rules the schema cannot express."""
    messages: list[str] = []
    records = document.get("records")

    if not isinstance(records, Sequence):
        return ["<root>: records must be a list"]

    if len(records) == 0:
        messages.append("<root>: document contains no records")

    seen: dict[str, int] = {}
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            messages.append(f"records/{index}: record must be an object")
            continue

        messages.extend(_check_identifier(record, index, seen))
        messages.extend(_check_timestamp(record, index))
        messages.extend(_check_location_consistency(record, index))

    return messages


def _check_identifier(record: Mapping[str, Any], index: int, seen: dict[str, int]) -> list[str]:
    identifier = record.get("id")
    if not isinstance(identifier, str):
        return []
    if identifier in seen:
        return [
            f"records/{index}: duplicate id, already used by record {seen[identifier]}. "
            "Identifiers are content hashes and must be unique within a document."
        ]
    seen[identifier] = index
    return []


def _check_timestamp(record: Mapping[str, Any], index: int) -> list[str]:
    raw = record.get("captured_at")
    if not isinstance(raw, str):
        return []
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        return [f"records/{index}: captured_at is not a parseable ISO 8601 timestamp"]
    if moment.tzinfo is None:
        return [
            f"records/{index}: captured_at has no UTC offset. "
            "Ordering across devices is impossible without one."
        ]
    return []


def _check_location_consistency(record: Mapping[str, Any], index: int) -> list[str]:
    location = record.get("location")
    source = record.get("location_source")

    if location is None and source is not None:
        return [
            f"records/{index}: location_source is set but location is absent. "
            "Remove the source or supply coordinates."
        ]
    return []
