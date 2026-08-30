"""The label on a schema, which validation never reads.

A document taken through both halves -- produced by the core, checked
against the published schema -- proves that the **shape** agrees. It
cannot prove that the **label** does. `$id` and `title` take no part in
validation, measured rather than assumed:

    as published                              validates: True
    $id replaced with audit-report-9.json      validates: True
    title replaced with "Something else"       validates: True
    $schema swapped for another dialect        validates: True

And a consumer reads the label first, to decide which schema to reach
for at all.

These checks are the alarm rather than the defence. The defence is
`test_interest_export_conformance.py`, which runs a real export through
the kit and fails five ways if either side of the identifier moves --
but it exists because #302 wanted the library's output checked against
its own contract, and the identifier coupling came free with it. **A
defence inherited from another purpose leaves with that purpose.**
Nothing here would have said so.

Every assertion compares two strings already on disk.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from kiseki.application.exporting import EXPORT_SCHEMA, EXPORT_SCHEMA_VERSION
from kiseki_conformance.contracts import INTEREST_EXPORT, PHOTO_RECORD, Contract

REPO_ROOT = Path(__file__).parents[2]
SCHEMAS = REPO_ROOT / "schemas"

PHOTO_RECORD_VERSION = "1.0"
"""What `kiseki_ingest` writes at the top of every document it emits."""

VERSION_IN_NAME = re.compile(r"-v(\d+)\.json$")

DIALECT = "https://json-schema.org/draft/2020-12/schema"
"""What the kit's validator is built for. A file claiming another
dialect is a file the kit reads by the wrong rules."""


def published(name: str) -> dict[str, Any]:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


class TestTheInterestExport:
    def test_the_schema_declares_the_name_the_core_emits(self) -> None:
        schema = published(INTEREST_EXPORT.resource)
        assert schema["properties"]["schema"]["const"] == EXPORT_SCHEMA

    def test_the_schema_declares_the_version_the_core_emits(self) -> None:
        schema = published(INTEREST_EXPORT.resource)
        assert schema["properties"]["version"]["const"] == EXPORT_SCHEMA_VERSION

    def test_the_kit_knows_it_by_the_name_the_core_emits(self) -> None:
        """`declared_by` carries the identifier as a literal, because the
        kit cannot import the core. This is that literal, checked."""
        assert INTEREST_EXPORT.declared_by({"schema": EXPORT_SCHEMA}) is True

    def test_the_file_name_says_the_version_the_schema_declares(self) -> None:
        match = VERSION_IN_NAME.search(INTEREST_EXPORT.resource)
        assert match, f"{INTEREST_EXPORT.resource} does not name a version"
        assert int(match.group(1)) == EXPORT_SCHEMA_VERSION


class TestPhotoRecord:
    def test_the_schema_declares_the_version_its_producer_writes(self) -> None:
        schema = published(PHOTO_RECORD.resource)
        assert schema["properties"]["schema_version"]["const"] == PHOTO_RECORD_VERSION

    def test_the_kit_knows_it_by_the_field_its_producer_writes(self) -> None:
        assert PHOTO_RECORD.declared_by({"schema_version": PHOTO_RECORD_VERSION}) is True

    def test_the_file_name_says_the_major_version_the_schema_declares(self) -> None:
        match = VERSION_IN_NAME.search(PHOTO_RECORD.resource)
        assert match, f"{PHOTO_RECORD.resource} does not name a version"
        assert match.group(1) == PHOTO_RECORD_VERSION.split(".")[0]


@pytest.mark.parametrize("contract", [PHOTO_RECORD, INTEREST_EXPORT], ids=lambda c: c.option)
class TestEverySchema:
    def test_it_is_published_where_the_kit_looks_for_it(self, contract: Contract) -> None:
        assert (SCHEMAS / contract.resource).is_file()

    def test_its_id_ends_with_its_own_file_name(self, contract: Contract) -> None:
        """A renamed file with a stale `$id` resolves references to the
        wrong document, and validates perfectly while doing it."""
        schema = published(contract.resource)
        assert schema["$id"].endswith(contract.resource)

    def test_its_title_names_the_contract_the_kit_calls_it(self, contract: Contract) -> None:
        """Not for validation -- for the person reading a violation."""
        schema = published(contract.resource)
        assert schema["title"] == contract.name

    def test_it_says_which_dialect_it_is_written_in(self, contract: Contract) -> None:
        """Swapped for another dialect, a schema still validates the same
        documents today and means something different -- `const` and
        `$ref` and `items` have all changed meaning between drafts. The
        one field that says how to read the file is the one field
        nothing reads."""
        assert published(contract.resource)["$schema"] == DIALECT
