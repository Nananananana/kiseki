"""The contracts this kit knows, and how a document says which it is.

A published contract is three things: a schema, a way of naming itself,
and the rules a schema cannot express. Everything specific to one
contract is a `Contract` value here; everything else in the package is
the same for all of them. A repository adding its own contract adds one
of these and nothing more.

Reading the name first is the discipline the contracts themselves
follow -- a consumer refuses what it does not recognise rather than
parsing it hopefully -- so a document that names nothing is refused
here too, rather than guessed at.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from kiseki_conformance import checks, interest_export, readings, schema


@dataclass(frozen=True)
class Contract:
    """One published contract, and everything the kit needs to check it."""

    name: str
    """What to call it in a message a person reads."""

    option: str
    """What to type after ``--contract``."""

    resource: str
    """The bundled schema file."""

    declared_by: Callable[[Mapping[str, Any]], bool]
    """Whether a document says it is one of these."""

    semantics: Callable[[Any], list[str]]
    """The rules the schema cannot express."""

    container: str | None
    """The key holding the list a summary counts, or None when the
    document **is** the list. NoteRecord and WebRecord are bare
    arrays, and this field assumed an object until they arrived
    (#373) -- the abstraction claimed a repository could add a
    contract "and nothing more", and could not express two of the
    four this repository already had."""

    unit: str
    """What one of those is called."""

    entry: str
    """The key under `$defs` describing one entry, for the check that
    proves the validator can still refuse (`test_the_checker_can_still
    _say_no`). Named rather than guessed: a schema may hold several
    definitions, and picking the first would be picking whichever the
    file happened to list first."""

    def violations(self, document: object) -> list[str]:
        """Every violation, structural and semantic, in one list."""
        messages = schema.violations(self.resource, document)
        if self.container is None or isinstance(document, Mapping):
            messages += self.semantics(document)
        return messages

    def summarise(self, document: object) -> str:
        """The line printed when a document conforms."""
        if self.container is None:
            return f"conforms to {self.name} ({readings.count(document)} {self.unit}(s))"
        entries = document.get(self.container, []) if isinstance(document, Mapping) else []
        count = len(entries) if isinstance(entries, list) else 0
        return f"conforms to {self.name} ({count} {self.unit}(s))"


PHOTO_RECORD = Contract(
    name="PhotoRecord v1",
    option="photo-record",
    resource=checks.SCHEMA_RESOURCE,
    declared_by=lambda document: "schema_version" in document,
    semantics=checks.check_semantics,
    container="records",
    unit="record",
    entry="photoRecord",
)

INTEREST_EXPORT = Contract(
    name="kiseki-interest-export v1",
    option="interest-export",
    resource=interest_export.SCHEMA_RESOURCE,
    declared_by=lambda document: document.get("schema") == "kiseki-interest-export",
    semantics=interest_export.check_export_semantics,
    container="interests",
    unit="interest",
    entry="interest",
)

NOTE_RECORD = Contract(
    name="NoteRecord v1",
    option="note-record",
    resource=readings.NOTE_SCHEMA_RESOURCE,
    declared_by=readings.anything,
    semantics=readings.check_note_semantics,
    container=None,
    unit="reading",
    entry="record",
)

WEB_RECORD = Contract(
    name="WebRecord v1",
    option="web-record",
    resource=readings.WEB_SCHEMA_RESOURCE,
    declared_by=readings.anything,
    semantics=readings.check_web_semantics,
    container=None,
    unit="reading",
    entry="record",
)

CONTRACTS = (PHOTO_RECORD, INTEREST_EXPORT, NOTE_RECORD, WEB_RECORD)

UNNAMEABLE = tuple(contract for contract in CONTRACTS if contract.container is None)
"""The contracts no document can claim, because neither shape has a
field for the claim. Named here so the command line can say which two
it is asking between, rather than reporting the same refusal a
malformed document gets."""

BY_OPTION = {contract.option: contract for contract in CONTRACTS}


def identify(document: object) -> Contract | None:
    """Which contract a document claims to be, or None if it claims none."""
    if not isinstance(document, Mapping):
        return None
    for contract in CONTRACTS:
        if contract.declared_by(document):
            return contract
    return None
