"""Strict at the door, tolerant in the room.

`docs/records.md` promises that a contract **ignores what it does not
know**: an unrecognised field is passed over, never refused, because a
producer may carry its own notes and a contract that argues with them
forces every producer to be written twice.

Every schema in `schemas/` sets `additionalProperties: false`, in all
eighteen places. Read side by side, those look like a contradiction.

They are two layers, and this pins both.

**The kit refuses.** A producer that claims to emit PhotoRecord and
emits PhotoRecord-plus-something is not emitting PhotoRecord, and
saying so is the kit's whole purpose -- it exists to tell somebody
writing a producer in Swift that their output is or is not acceptable,
and "acceptable, with an unexplained field" is not an answer they can
act on.

**The reader ignores.** The core is not the kit. It is one program
reading a document somebody else wrote, and refusing a photograph
because a producer left a note beside it would lose the photograph for
nothing.

The layering is deliberate and was never written down, which is the
part worth fixing: both halves are checked here, and both documents
now say so.
"""

import json
import os
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqlitePhotoRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.interfaces.cli import EXIT_OK, main
from kiseki_conformance import validate_document

FIXTURES = Path(__file__).parents[1] / "fixtures" / "photo_record"


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def with_extra_fields() -> dict[str, object]:
    """A valid document, plus two fields no contract mentions."""
    document = json.loads((FIXTURES / "valid_minimal.json").read_text(encoding="utf-8"))
    document["records"][0]["producer_note"] = "carried by the producer, for the producer"
    document["exported_by"] = "some tool, version 4"
    return document


def test_the_kit_refuses_what_the_contract_does_not_mention() -> None:
    violations = validate_document(with_extra_fields())
    assert any("producer_note" in message for message in violations)
    assert any("exported_by" in message for message in violations)


def test_the_reader_passes_it_over(tmp_path: Path) -> None:
    """The same document, taken in without complaint."""
    records = tmp_path / "records.json"
    records.write_text(json.dumps(with_extra_fields()), encoding="utf-8")

    assert main(["--data-root", str(tmp_path), "ingest", str(records)]) == EXIT_OK

    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    assert len(SqlitePhotoRepository(connection).all()) == 1


def test_what_was_stored_carries_none_of_it(tmp_path: Path) -> None:
    """Ignoring is not keeping. The field is passed over, not filed
    away somewhere for later."""
    records = tmp_path / "records.json"
    records.write_text(json.dumps(with_extra_fields()), encoding="utf-8")
    main(["--data-root", str(tmp_path), "ingest", str(records)])

    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    text = paths.db_path.read_bytes()
    assert b"producer_note" not in text
    assert b"some tool, version 4" not in text
