"""Bundled schemas, and validation against one of them.

Nothing here knows which contract it is checking. A published contract
is three things -- a schema, a way of naming itself, and the handful of
rules a schema cannot express -- and this module is the first of them.
It is the part of the kit that any repository with a contract of its
own can copy unchanged.
"""

import json
from functools import cache
from importlib.resources import files
from typing import Any


def load(resource: str) -> dict[str, Any]:
    """Return one of the bundled schemas, by file name."""
    text = files("kiseki_conformance").joinpath("schemas", resource).read_text(encoding="utf-8")
    schema: dict[str, Any] = json.loads(text)
    return schema


@cache
def _validator(resource: str) -> Any:
    from jsonschema import Draft202012Validator

    return Draft202012Validator(load(resource))


def violations(resource: str, document: object) -> list[str]:
    """Return schema violations as readable messages. Empty means valid."""
    messages: list[str] = []
    for error in _validator(resource).iter_errors(document):
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        messages.append(f"{location}: {error.message}")
    return sorted(messages)
