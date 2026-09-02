"""Reusable pytest suites for producers written in Python.

Subclass the one for your contract and supply the document you emit:

    from kiseki_conformance import PhotoRecordConformance

    class TestMyExporter(PhotoRecordConformance):
        @pytest.fixture
        def document(self):
            return my_exporter.export(sample_directory)

Producers written in other languages should use the command line
interface instead: ``kiseki-conformance output.json``.

The checks every contract shares live on `ContractConformance`; each
subclass adds only what is true of its own contract.
"""

from collections.abc import Mapping
from typing import Any, ClassVar

import pytest

from kiseki_conformance import schema
from kiseki_conformance.contracts import INTEREST_EXPORT, PHOTO_RECORD, Contract, identify


class ContractConformance:
    """Checks any document must pass to be one of ours."""

    contract: ClassVar[Contract]

    @pytest.fixture
    def document(self) -> Mapping[str, Any]:
        raise NotImplementedError("Override the 'document' fixture with your producer's output")

    def test_document_matches_schema(self, document: Mapping[str, Any]) -> None:
        errors = schema.violations(self.contract.resource, document)
        assert not errors, "schema violations:\n" + "\n".join(errors)

    def test_document_is_semantically_consistent(self, document: Mapping[str, Any]) -> None:
        errors = self.contract.semantics(document)
        assert not errors, "semantic violations:\n" + "\n".join(errors)

    def test_document_names_its_contract(self, document: Mapping[str, Any]) -> None:
        """A reader identifies a document before parsing it, and a
        document that names nothing cannot be identified."""
        assert identify(document) is self.contract


class PhotoRecordConformance(ContractConformance):
    """Checks every PhotoRecord producer must pass."""

    contract = PHOTO_RECORD

    def test_document_declares_supported_version(self, document: Mapping[str, Any]) -> None:
        assert document.get("schema_version") == "1.0"

    def test_the_document_had_something_to_check(self, document: Mapping[str, Any]) -> None:
        """Every per-record check below is a loop, and a loop over
        nothing passes. A producer whose document came out empty would
        otherwise read a green run as *my records are correct*, when
        what happened is that there were no records."""
        assert document.get("records"), (
            "this document carries no records, so every per-record check "
            "in this suite had nothing to check and passed by default. "
            "Run the suite against a document your producer actually emits."
        )

    def test_every_record_declares_consent(self, document: Mapping[str, Any]) -> None:
        records = document.get("records", [])
        missing = [
            index
            for index, record in enumerate(records)
            if not isinstance(record.get("consent"), Mapping)
        ]
        assert not missing, f"records without consent: {missing}"


class InterestExportConformance(ContractConformance):
    """Checks every producer of a kiseki-interest-export must pass.

    The last two are what a consumer outside this repository relies on:
    an interest with no confidence is an opinion wearing a fact's
    clothes, and a place topic is a movement history (ADR-0047).
    """

    contract = INTEREST_EXPORT

    def test_document_declares_supported_version(self, document: Mapping[str, Any]) -> None:
        assert document.get("schema") == "kiseki-interest-export"
        assert document.get("version") == 1

    def test_the_document_had_something_to_check(self, document: Mapping[str, Any]) -> None:
        """As above. Note which check this does *not* guard:
        `test_no_place_ever_leaves` is honest on an empty document,
        because a document with nothing in it really does leak no
        place. A negative check needs no population."""
        assert document.get("interests"), (
            "this document carries no interests, so every per-interest "
            "check in this suite had nothing to check and passed by "
            "default. Run the suite against a document your producer "
            "actually emits."
        )

    def test_every_interest_carries_its_confidence(self, document: Mapping[str, Any]) -> None:
        interests = document.get("interests", [])
        missing = [
            index
            for index, interest in enumerate(interests)
            if not isinstance(interest.get("confidence"), int | float)
            or isinstance(interest.get("confidence"), bool)
        ]
        assert not missing, f"interests without confidence: {missing}"

    def test_no_place_ever_leaves(self, document: Mapping[str, Any]) -> None:
        entries = list(document.get("interests", [])) + list(document.get("stages", []))
        places = [
            entry.get("topic")
            for entry in entries
            if str(entry.get("topic", "")).startswith("place:")
        ]
        assert not places, f"place topics in the export: {places}"
