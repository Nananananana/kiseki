"""Exercise the conformance kit against the reference fixtures."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from kiseki_conformance import (
    PhotoRecordConformance,
    check_semantics,
    load_schema,
    validate_document,
)
from kiseki_conformance.cli import EXIT_OK, EXIT_UNREADABLE, EXIT_VIOLATIONS, main

REPO_ROOT = Path(__file__).parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "photo_record"
CANONICAL_SCHEMA = REPO_ROOT / "schemas" / "photo-record-v1.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fixtures(prefix: str) -> list[Path]:
    found = sorted(FIXTURE_DIR.glob(f"{prefix}_*.json"))
    assert found, f"no fixtures found for prefix {prefix!r}"
    return found


def test_bundled_schema_matches_the_published_one() -> None:
    """The packaged copy must not drift from the one published in the repository."""
    assert load_schema() == load(CANONICAL_SCHEMA)


@pytest.mark.parametrize("path", fixtures("valid"), ids=lambda p: p.stem)
def test_valid_fixtures_report_no_violations(path: Path) -> None:
    document = load(path)
    assert validate_document(document) == []
    assert check_semantics(document) == []


@pytest.mark.parametrize("path", fixtures("invalid"), ids=lambda p: p.stem)
def test_invalid_fixtures_report_violations(path: Path) -> None:
    assert validate_document(load(path)) != []


def test_duplicate_identifiers_are_reported() -> None:
    record = load(FIXTURE_DIR / "valid_minimal.json")["records"][0]
    document = {"schema_version": "1.0", "records": [record, dict(record)]}

    assert validate_document(document) == []
    violations = check_semantics(document)
    assert any("duplicate id" in message for message in violations)


def test_naive_timestamp_is_reported_by_semantics() -> None:
    document = {
        "schema_version": "1.0",
        "records": [{"id": "sha256:x", "captured_at": "2025-05-03T10:24:31"}],
    }
    violations = check_semantics(document)
    assert any("UTC offset" in message for message in violations)


def test_location_source_without_location_is_reported() -> None:
    document = {
        "schema_version": "1.0",
        "records": [{"location": None, "location_source": "measured"}],
    }
    violations = check_semantics(document)
    assert any("location_source" in message for message in violations)


def test_empty_document_is_reported() -> None:
    assert check_semantics({"schema_version": "1.0", "records": []}) != []


class TestReferenceDocumentConformance(PhotoRecordConformance):
    """Demonstrates how a producer plugs its own output into the suite."""

    @pytest.fixture
    def document(self) -> Mapping[str, Any]:
        result: Mapping[str, Any] = load(FIXTURE_DIR / "valid_full.json")
        return result


class TestCli:
    def test_accepts_a_valid_document(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main([str(FIXTURE_DIR / "valid_full.json"), "--quiet"]) == EXIT_OK
        assert capsys.readouterr().out == ""

    def test_rejects_an_invalid_document(self) -> None:
        assert main([str(FIXTURE_DIR / "invalid_id_format.json"), "--quiet"]) == EXIT_VIOLATIONS

    def test_reports_a_missing_file(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / "absent.json"), "--quiet"]) == EXIT_UNREADABLE

    def test_reports_malformed_json(self, tmp_path: Path) -> None:
        broken = tmp_path / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        assert main([str(broken), "--quiet"]) == EXIT_UNREADABLE

    def test_prints_a_summary_when_not_quiet(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main([str(FIXTURE_DIR / "valid_full.json")]) == EXIT_OK
        assert "conforms to PhotoRecord v1" in capsys.readouterr().out
