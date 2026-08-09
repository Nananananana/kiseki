"""Conformance test kit for PhotoRecord producers.

A producer is any program that emits PhotoRecord documents. It does not need to
be written in Python, and it does not need to import the core library. This kit
verifies that its output is acceptable.
"""

from kiseki_conformance.checks import (
    check_semantics,
    load_schema,
    validate_document,
)
from kiseki_conformance.suite import PhotoRecordConformance

__all__ = [
    "PhotoRecordConformance",
    "check_semantics",
    "load_schema",
    "validate_document",
]
