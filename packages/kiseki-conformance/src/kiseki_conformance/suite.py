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

import copy
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar

import pytest

from kiseki_conformance import schema
from kiseki_conformance.contracts import (
    INTEREST_EXPORT,
    NOTE_RECORD,
    PHOTO_RECORD,
    WEB_RECORD,
    Contract,
    identify,
)


class ContractConformance:
    """Checks any document must pass to be one of ours."""

    contract: ClassVar[Contract]

    @pytest.fixture
    def document(self) -> Any:
        raise NotImplementedError("Override the 'document' fixture with your producer's output")

    def test_document_matches_schema(self, document: Any) -> None:
        errors = schema.violations(self.contract.resource, document)
        assert not errors, "schema violations:\n" + "\n".join(errors)

    def test_document_is_semantically_consistent(self, document: Any) -> None:
        errors = self.contract.semantics(document)
        assert not errors, "semantic violations:\n" + "\n".join(errors)

    def test_document_names_its_contract(self, document: Any) -> None:
        """A reader identifies a document before parsing it.

        Two of the four contracts have nowhere to put the claim --
        `NoteRecord v1` and `WebRecord v1` are bare arrays of the same
        six field names -- so for those the right answer is that the
        kit does **not** identify them. Guessing from the reference
        prefix would couple the kit to something the contract refuses
        to promise (`docs/note-record.md`).
        """
        if self.contract.container is None:
            assert identify(document) is None, (
                f"{self.contract.name} has no field that names it, so a kit that "
                "identified this document identified it by guessing."
            )
            return
        assert identify(document) is self.contract

    def test_the_checker_can_still_say_no(self, document: Any) -> None:
        """This kit is run by people who cannot see our CI.

        Every document a conformance kit is given is one its producer
        believes is correct, so a kit whose validator had quietly
        stopped validating prints exactly what a working one prints.
        Raised by the seam session, who found the five documents in
        their own checker were all made by the party that publishes
        the schema: **always passing, and identical output if the
        check were removed.**

        So the suite proves its own negative capability, against the
        producer's own document: take away a property the schema
        requires, and the validator has to refuse what it just
        accepted.
        """
        definitions = schema.load(self.contract.resource)
        entry = definitions.get("$defs", {}).get(self.contract.entry, definitions)
        names = entry.get("required")
        assert names, (
            f"{self.contract.name}'s schema requires no property, so nothing can be "
            "taken away -- and this kit would accept a document of the right shape "
            "with nothing in it."
        )
        spoiled = _without(document, names[0], self.contract.container)
        assert schema.violations(self.contract.resource, spoiled), (
            f"the validator accepted a document with {names[0]!r} removed, so it is "
            "not validating. Every document you give this kit is one you believe is "
            "correct, which is why this is the only way to tell."
        )


def _without(document: Any, field: str, container: str | None) -> Any:
    """The same document with one required field taken out of its first
    entry -- or out of the document itself, where the entries are it."""
    spoiled = copy.deepcopy(document)
    entries = spoiled if container is None else spoiled.get(container)
    if isinstance(entries, Sequence) and entries and isinstance(entries[0], dict):
        entries[0].pop(field, None)
        return spoiled
    if isinstance(spoiled, dict):
        spoiled.pop(field, None)
    return spoiled


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


class NoteRecordConformance(ContractConformance):
    """Checks every NoteRecord producer must pass.

    The text never travels, so what this can check is the shape and
    the one rule a schema cannot express: a sensitive category arrives
    with no labels, or the document is refused rather than tidied.
    """

    contract = NOTE_RECORD


class WebRecordConformance(ContractConformance):
    """Checks every WebRecord producer must pass.

    The same shape as NoteRecord and a different contract: seven
    categories carry no labels here against five there, because a
    symptom typed into a search box at two in the morning is not the
    deliberate act that writing a note about an illness is.
    """

    contract = WEB_RECORD
