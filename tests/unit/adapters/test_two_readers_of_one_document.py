"""Two ways to read a PhotoRecord document, and they must agree.

One parses the whole file and hands back its records; the other hands
back each record as it is parsed. Same contract, two implementations,
and the second exists because the first costs 4.7 times the file in
memory -- measured at 546 MB peak for a 116 MB document, which
extrapolates to about 2.7 GB for the million-record documents the
projects beside this one advertise handling.

**They disagreed the first time, and sqlite3 was what noticed.**
`ijson` decodes a JSON number to `Decimal` by default and `json`
decodes it to `float`, so the streaming reader produced latitudes the
store refused outright:

    Error binding parameter 3: type 'decimal.Decimal' is not supported

That is the good version of this failure -- loud, immediate, on the
first test that stored anything. The bad version is a reader that
agrees about types and disagrees about, say, a field whose value is
`null`, which nothing would have said.

So this file compares them on documents built to be awkward, rather
than trusting that two readers of one format are one reader.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from kiseki.adapters.records import (
    STREAMING,
    WHOLE,
    is_streaming_available,
    read_streaming,
    read_whole,
    reader,
)

REPO_ROOT = Path(__file__).parents[3]
VALID = REPO_ROOT / "tests" / "fixtures" / "photo_record" / "valid_full.json"


def a_record(index: int, **rest: Any) -> dict[str, Any]:
    base = json.loads(VALID.read_text(encoding="utf-8"))["records"][0]
    return dict(base, id=f"sha256:{index:064d}", **rest)


def written(tmp_path: Path, records: list[dict[str, Any]], **document: Any) -> Path:
    path = tmp_path / "photo-records.json"
    body: dict[str, Any] = {"schema_version": "1.0", "records": records}
    body.update(document)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_the_extra_is_installed_here() -> None:
    """Asserted rather than skipped around. `ijson` is a dev
    dependency, so a `skipif` would never fire -- and would fire
    silently the day it was dropped, turning every comparison below
    into nothing while the run stayed green."""
    assert is_streaming_available(), "run `uv sync --all-packages`"


class TestTheyAgree:
    """The comparison, on documents chosen to be awkward."""

    def compare(self, path: Path) -> None:
        whole = list(read_whole(path))
        streamed = list(read_streaming(path))
        assert whole == streamed, "the two readers disagree about this document"

    def test_on_the_fixture_this_repository_ships(self) -> None:
        self.compare(VALID)

    def test_on_many_records(self, tmp_path: Path) -> None:
        self.compare(written(tmp_path, [a_record(index) for index in range(250)]))

    def test_on_no_records_at_all(self, tmp_path: Path) -> None:
        """An owner with no photographs is a real state."""
        self.compare(written(tmp_path, []))

    def test_the_types_match_and_not_only_the_values(self, tmp_path: Path) -> None:
        """The failure that got through: `Decimal` and `float` compare
        equal, so a value comparison alone would have passed while the
        store refused to bind it."""
        path = written(tmp_path, [a_record(0)])
        whole = next(iter(read_whole(path)))
        streamed = next(iter(read_streaming(path)))
        for key, value in whole["location"].items():
            assert type(streamed["location"][key]) is type(value), (
                f"{key}: whole gives {type(value).__name__}, "
                f"streaming gives {type(streamed['location'][key]).__name__}"
            )

    def test_a_coordinate_survives_as_something_sqlite_can_store(self, tmp_path: Path) -> None:
        """The check with teeth, rather than a type comparison that
        would pass for two wrong types that matched."""
        import sqlite3

        path = written(tmp_path, [a_record(0)])
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE probe (lat, lon)")
        for records in (read_whole(path), read_streaming(path)):
            for record in records:
                connection.execute(
                    "INSERT INTO probe VALUES (?, ?)",
                    (record["location"]["lat"], record["location"]["lon"]),
                )
        connection.close()

    def test_on_a_null_a_nested_object_and_a_unicode_field(self, tmp_path: Path) -> None:
        """Three shapes a parser can differ about quietly."""
        self.compare(
            written(
                tmp_path,
                [
                    a_record(0, thumbnail_ref=None),
                    a_record(1, producer_note={"deep": {"deeper": [1, 2, 3]}}),
                    a_record(2, producer_note="温泉 · café — 𩸽"),
                ],
            )
        )

    def test_an_unknown_top_level_key_changes_neither(self, tmp_path: Path) -> None:
        """Rule two of docs/records.md, from the reader's side."""
        self.compare(written(tmp_path, [a_record(0)], produced_by="something else"))


class TestWhatEachRefuses:
    def test_neither_accepts_a_document_with_no_records_key(self, tmp_path: Path) -> None:
        """A document with `"records": []` and a document with no
        `records` at all are both nothing to a streaming parser, and
        they are not the same thing: the first is an owner with no
        photographs, the second is the wrong file."""
        path = tmp_path / "wrong.json"
        path.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
        for read in (read_whole, read_streaming):
            with pytest.raises(ValueError, match="no 'records' key"):
                list(read(path))

    def test_an_empty_records_array_is_accepted_by_both(self, tmp_path: Path) -> None:
        path = written(tmp_path, [])
        assert list(read_whole(path)) == []
        assert list(read_streaming(path)) == []

    def test_streaming_says_which_record_it_stopped_at(self, tmp_path: Path) -> None:
        """Most of why this exists. The whole-document reader parses
        everything and then fails about the document; a 2 GB file
        broken near the end costs minutes and gigabytes to say so, and
        says it about the file."""
        path = tmp_path / "broken.json"
        good = ",".join(json.dumps(a_record(index)) for index in range(30))
        path.write_text(
            '{"schema_version": "1.0", "records": [' + good + ", {oops}]}", encoding="utf-8"
        )
        with pytest.raises(ValueError, match="record 30"):
            list(read_streaming(path))

    def test_the_whole_reader_fails_about_the_document(self, tmp_path: Path) -> None:
        """The contrast, pinned rather than asserted in prose."""
        path = tmp_path / "broken.json"
        path.write_text('{"schema_version": "1.0", "records": [{oops}]}', encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            list(read_whole(path))


class TestChoosingOne:
    def test_streaming_is_used_when_the_extra_is_there(self, tmp_path: Path) -> None:
        _, which = reader(written(tmp_path, [a_record(0)]))
        assert which == STREAMING

    def test_the_whole_reader_can_be_asked_for(self, tmp_path: Path) -> None:
        """So a reader who suspects the streaming one can compare, and
        so this test file can."""
        _, which = reader(written(tmp_path, [a_record(0)]), prefer_streaming=False)
        assert which == WHOLE

    def test_both_names_are_reported_and_not_guessed(self, tmp_path: Path) -> None:
        """The command prints which reader ran. A library that chose
        silently would leave a memory difference of three orders of
        magnitude unexplainable."""
        assert {WHOLE, STREAMING} == {"whole", "streaming"}
