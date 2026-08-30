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

from kiseki_conformance import checks, interest_export, schema


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

    semantics: Callable[[Mapping[str, Any]], list[str]]
    """The rules the schema cannot express."""

    container: str
    """The key holding the list a summary counts."""

    unit: str
    """What one of those is called."""

    def violations(self, document: object) -> list[str]:
        """Every violation, structural and semantic, in one list."""
        messages = schema.violations(self.resource, document)
        if isinstance(document, Mapping):
            messages += self.semantics(document)
        return messages

    def summarise(self, document: object) -> str:
        """The line printed when a document conforms."""
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
)

INTEREST_EXPORT = Contract(
    name="kiseki-interest-export v1",
    option="interest-export",
    resource=interest_export.SCHEMA_RESOURCE,
    declared_by=lambda document: document.get("schema") == "kiseki-interest-export",
    semantics=interest_export.check_export_semantics,
    container="interests",
    unit="interest",
)

CONTRACTS = (PHOTO_RECORD, INTEREST_EXPORT)

BY_OPTION = {contract.option: contract for contract in CONTRACTS}


def identify(document: object) -> Contract | None:
    """Which contract a document claims to be, or None if it claims none."""
    if not isinstance(document, Mapping):
        return None
    for contract in CONTRACTS:
        if contract.declared_by(document):
            return contract
    return None
