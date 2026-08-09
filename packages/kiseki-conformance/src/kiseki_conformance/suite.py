"""A reusable pytest suite for producers written in Python.

Subclass it and supply the document your producer emits:

    from kiseki_conformance import PhotoRecordConformance

    class TestMyExporter(PhotoRecordConformance):
        @pytest.fixture
        def document(self):
            return my_exporter.export(sample_directory)

Producers written in other languages should use the command line interface
instead: ``kiseki-conformance output.json``.
"""

from collections.abc import Mapping
from typing import Any

import pytest

from kiseki_conformance.checks import check_semantics, validate_document


class PhotoRecordConformance:
    """Checks every PhotoRecord producer must pass."""

    @pytest.fixture
    def document(self) -> Mapping[str, Any]:
        raise NotImplementedError("Override the 'document' fixture with your producer's output")

    def test_document_matches_schema(self, document: Mapping[str, Any]) -> None:
        errors = validate_document(document)
        assert not errors, "schema violations:\n" + "\n".join(errors)

    def test_document_is_semantically_consistent(self, document: Mapping[str, Any]) -> None:
        errors = check_semantics(document)
        assert not errors, "semantic violations:\n" + "\n".join(errors)

    def test_document_declares_supported_version(self, document: Mapping[str, Any]) -> None:
        assert document.get("schema_version") == "1.0"

    def test_every_record_declares_consent(self, document: Mapping[str, Any]) -> None:
        records = document.get("records", [])
        missing = [
            index
            for index, record in enumerate(records)
            if not isinstance(record.get("consent"), Mapping)
        ]
        assert not missing, f"records without consent: {missing}"
