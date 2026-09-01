"""The core reads what the web producer wrote, and nothing more.

A fourth input contract, independent of the other three. What arrives
is a reference, a day, a category and some labels; what does not is an
address, a title, a host or a time of day, because `WebRecord v1` has
nowhere to put any of them.
"""

import json
import os
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqlitePageReadingRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _document(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    path = tmp_path / "web-records.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def _record(reference: str, day: str = "2026-08-30", **rest: object) -> dict[str, object]:
    record: dict[str, object] = {
        "owner": "me",
        "platform": "firefox",
        "day": day,
        "reference": reference,
        "category": "reading",
        "labels": ["raft"],
    }
    record.update(rest)
    return record


def _held(tmp_path: Path) -> tuple[object, ...]:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    return SqlitePageReadingRepository(connect(paths.db_path)).all()


def test_a_document_is_taken_in(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    document = _document(tmp_path, [_record("page:aaaa"), _record("page:bbbb")])
    assert main(["--data-root", str(tmp_path), "web", str(document)]) == EXIT_OK
    assert "readings read 2" in capsys.readouterr().out
    assert len(_held(tmp_path)) == 2


def test_reading_it_again_replaces_rather_than_doubles(tmp_path: Path) -> None:
    document = _document(tmp_path, [_record("page:aaaa")])
    main(["--data-root", str(tmp_path), "web", str(document)])
    main(["--data-root", str(tmp_path), "web", str(document)])
    assert len(_held(tmp_path)) == 1


def test_the_same_page_on_a_later_day_is_another_reading(tmp_path: Path) -> None:
    first = _document(tmp_path, [_record("page:aaaa", day="2026-08-30")])
    main(["--data-root", str(tmp_path), "web", str(first)])
    second = _document(tmp_path, [_record("page:aaaa", day="2026-11-02")])
    main(["--data-root", str(tmp_path), "web", str(second)])
    assert len(_held(tmp_path)) == 2


def test_a_category_that_carries_no_labels_arriving_with_labels_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Refused, not trimmed: a core that tidied it would be hiding a
    producer that had stopped keeping its promise."""
    document = _document(tmp_path, [_record("page:aaaa", category="health", labels=["a clinic"])])
    assert main(["--data-root", str(tmp_path), "web", str(document)]) == EXIT_BAD_INPUT
    assert "could not be read" in capsys.readouterr().err
    assert _held(tmp_path) == ()


def test_an_unknown_field_is_passed_over(tmp_path: Path) -> None:
    """Rule two of docs/records.md, from the reader's side."""
    document = _document(tmp_path, [_record("page:aaaa", producer_note="carried by the producer")])
    assert main(["--data-root", str(tmp_path), "web", str(document)]) == EXIT_OK
    assert len(_held(tmp_path)) == 1


def test_a_document_that_is_not_a_list_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "web-records.json"
    path.write_text(json.dumps({"records": []}), encoding="utf-8")
    assert main(["--data-root", str(tmp_path), "web", str(path)]) == EXIT_BAD_INPUT


def test_a_byte_order_mark_is_survived(tmp_path: Path) -> None:
    """Producers on Windows write one without being asked (records.md)."""
    path = tmp_path / "web-records.json"
    path.write_text(json.dumps([_record("page:aaaa")]), encoding="utf-8-sig")
    assert main(["--data-root", str(tmp_path), "web", str(path)]) == EXIT_OK
    assert len(_held(tmp_path)) == 1


def test_nothing_of_the_address_can_arrive(tmp_path: Path) -> None:
    """There is no field for one, so a producer that tried would have
    it ignored rather than stored."""
    document = _document(
        tmp_path, [_record("page:aaaa", url="https://clinic.example.org/appointments")]
    )
    main(["--data-root", str(tmp_path), "web", str(document)])
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    assert b"clinic.example.org" not in paths.db_path.read_bytes()


class TestADocumentThatSharesNothing:
    """A library that already holds readings, given a document naming
    none of them, is looking at a new source or at the same one
    re-identified (ADR-0086). The two are indistinguishable from the
    document, and the second doubles every trail while looking like the
    first."""

    def test_the_first_import_says_nothing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """There is nothing to share a reference with."""
        document = _document(tmp_path, [_record("page:aaaa")])
        main(["--data-root", str(tmp_path), "web", str(document)])
        assert "share a reference" not in capsys.readouterr().out

    def test_a_second_document_that_overlaps_says_nothing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        first = _document(tmp_path, [_record("page:aaaa")])
        main(["--data-root", str(tmp_path), "web", str(first)])
        second = _document(tmp_path, [_record("page:aaaa"), _record("page:bbbb")])
        main(["--data-root", str(tmp_path), "web", str(second)])
        assert "share a reference" not in capsys.readouterr().out

    def test_a_second_document_that_overlaps_with_nothing_says_so(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        first = _document(tmp_path, [_record("page:aaaa")])
        main(["--data-root", str(tmp_path), "web", str(first)])
        second = _document(tmp_path, [_record("page:cccc"), _record("page:dddd")])
        main(["--data-root", str(tmp_path), "web", str(second)])
        printed = capsys.readouterr().out
        assert "share a reference" in printed
        assert "ADR-0086" in printed

    def test_it_refuses_nothing(self, tmp_path: Path) -> None:
        """A second folder shares nothing either, and that is fine."""
        first = _document(tmp_path, [_record("page:aaaa")])
        main(["--data-root", str(tmp_path), "web", str(first)])
        second = _document(tmp_path, [_record("page:cccc")])
        assert main(["--data-root", str(tmp_path), "web", str(second)]) == EXIT_OK
        assert len(_held(tmp_path)) == 2
