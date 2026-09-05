"""`kiseki limits` on a library that was actually ingested.

The unit tests beside this one exercise `limits_of` on constructed
counts, which is the right way to check the arithmetic and the wrong
way to check the command: #364 asks for a report computed from an
installation's own data, and a test built only from fixtures would
pass just as happily against a command that recited.

So this ingests real records through the real CLI and reads what comes
out of the other end.
"""

import json
import os
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def a_library(tmp_path: Path) -> Path:
    """Eight photographs across two days, and nothing else at all."""
    records = [
        {
            "id": f"sha256:{index:064d}",
            "captured_at": f"2025-05-0{1 + index // 4}T10:{index:02d}:00+09:00",
            "location": {"lat": 35.0094, "lon": 135.6669, "accuracy_m": 12},
            "location_source": "measured",
            "media_type": "image",
            "content_kind": "photo",
            "thumbnail_ref": f"2025/05/{index:04d}.jpg",
            "owner": {"id": "me", "device": "a phone"},
            "consent": {"granted": True, "scope": ["preferences"]},
        }
        for index in range(8)
    ]
    document = tmp_path / "photo-records.json"
    document.write_text(json.dumps({"schema_version": "1.0", "records": records}), encoding="utf-8")
    assert main(["--data-root", str(tmp_path), "ingest", str(document)]) == EXIT_OK
    assert main(["--data-root", str(tmp_path), "build"]) == EXIT_OK
    return tmp_path


def printed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> str:
    assert main(["--data-root", str(tmp_path), "limits"]) == EXIT_OK
    return capsys.readouterr().out


def document_of(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> dict:
    assert main(["--data-root", str(tmp_path), "limits", "--json"]) == EXIT_OK
    raw = capsys.readouterr().out
    return json.loads(raw[raw.index("{") :])


def test_it_reports_the_span_it_actually_ingested(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two days of photographs, said as two days."""
    out = printed(a_library(tmp_path), capsys)
    assert "2025-05-01 to 2025-05-02" in out
    assert "covers 2 days" in out


def test_each_source_prints_the_days_it_covers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A source's own span, beside the library's, so a reader can see
    that one of them covers a fraction of the other."""
    out = printed(a_library(tmp_path), capsys)
    assert "2 days   2025-05-01 to 2025-05-02" in out


def test_it_names_the_sources_this_installation_lacks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A library of photographs alone cannot speak about what the
    owner wrote or read, and says which."""
    out = printed(a_library(tmp_path), capsys)
    for absent in ("notes", "pages", "activity", "screens"):
        assert absent in out
    assert "what you wrote for yourself" in out
    assert "what you read" in out


def test_the_unseeable_are_printed_even_on_a_healthy_library(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """They are always in force, so silence would teach the reader
    that a quiet report means no limits."""
    out = printed(a_library(tmp_path), capsys)
    assert "what no count can reach" in out
    assert "an interest you never photographed" in out


def test_an_empty_library_says_so_rather_than_printing_a_span(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = printed(tmp_path, capsys)
    assert "nothing has been read yet" in out
    assert "kiseki ingest" in out


def test_the_document_carries_the_counts_and_no_test_names(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A consumer cannot run this repository's tests, and a claim is
    not more true for naming one to a stranger."""
    payload = document_of(a_library(tmp_path), capsys)
    assert payload["span"] == {"first": "2025-05-01", "last": "2025-05-02", "days": 2}
    counts = {source["name"]: source["count"] for source in payload["sources"]}
    assert counts == {
        "photographs": 8,
        "notes": 0,
        "pages": 0,
        "activity": 0,
        "screens": 0,
    }
    assert payload["empty"] is False
    assert [one["subject"] for one in payload["unseeable"]]
    assert "tests/" not in json.dumps(payload)


def test_no_coordinate_reaches_the_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The library ingested a real coordinate. A limits report is a
    new outlet, and every new outlet has to be checked: the prompt
    path leaked one the first time it was written (ADR-0047)."""
    library = a_library(tmp_path)
    printed_out = printed(library, capsys)
    payload_text = json.dumps(document_of(library, capsys))
    for surface in (printed_out, payload_text):
        assert "35.0094" not in surface
        assert "135.6669" not in surface
        assert "35.00" not in surface
        assert "135.66" not in surface


def test_a_photograph_with_no_coordinate_is_said_out_loud(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Ingested with a time and no location -- which the contract allows --
    and reported as a limit rather than folded into the photographs row."""
    records = [
        {
            "id": f"sha256:{9:064d}",
            "captured_at": "2025-05-03T10:00:00+09:00",
            "media_type": "image",
            "content_kind": "photo",
            "thumbnail_ref": "2025/05/9999.jpg",
            "owner": {"id": "me", "device": "a phone"},
            "consent": {"granted": True, "scope": ["preferences"]},
        }
    ]
    document = tmp_path / "unplaced.json"
    document.write_text(json.dumps({"schema_version": "1.0", "records": records}), encoding="utf-8")
    library = a_library(tmp_path)
    assert main(["--data-root", str(library), "ingest", str(document)]) == EXIT_OK
    out = printed(library, capsys)
    assert "photographs without a place 1" in out or "photographs without a place" in out
    payload = document_of(library, capsys)
    subjects = {one["subject"]: one["reading"] for one in payload["limits"]}
    assert subjects["photographs without a place"] == "1"
