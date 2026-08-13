"""Specification for the command line interface."""

import json
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main

RECORDS = {
    "schema_version": "1.0",
    "records": [
        {
            "id": f"sha256:{index:064x}",
            "captured_at": f"2026-05-03T09:{index * 10:02d}:00+09:00",
            "location": {"lat": 35.0, "lon": 135.0},
            "location_source": "measured",
            "media_type": "image",
            "content_kind": "photo",
            "thumbnail_ref": f"2026/05/{index:016x}.jpg",
            "owner": {"owner_id": "u1"},
            "consent": {"use_for_preference": True, "use_for_story": True},
        }
        for index in range(6)
    ],
}


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate from the developer's own .env as well as their environment.

    The command line reads a dotenv file from the working directory. A test that
    did not move out of the repository would pick up whatever the developer has
    configured, and pass or fail depending on their machine.
    """
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "data"
    monkeypatch.setenv("KISEKI_DATA_ROOT", str(root))
    return root


@pytest.fixture
def records(tmp_path: Path) -> Path:
    path = tmp_path / "photo-records.json"
    path.write_text(json.dumps(RECORDS), encoding="utf-8")
    return path


class TestInvocation:
    def test_running_with_no_command_explains_itself(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main([]) == EXIT_BAD_INPUT
        assert "usage" in capsys.readouterr().err.lower()

    def test_reports_where_it_will_put_things(
        self, data_root: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["paths"]) == EXIT_OK
        assert str(data_root) in capsys.readouterr().out


class TestIngest:
    def test_takes_in_a_record_document(
        self, records: Path, data_root: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["ingest", str(records)]) == EXIT_OK
        assert "6" in capsys.readouterr().out

    def test_creates_the_database(self, records: Path, data_root: Path) -> None:
        main(["ingest", str(records)])
        assert (data_root / "db" / "kiseki.sqlite3").exists()

    def test_rejects_a_missing_file(self, tmp_path: Path, data_root: Path) -> None:
        assert main(["ingest", str(tmp_path / "absent.json")]) == EXIT_BAD_INPUT

    def test_rejects_a_document_that_is_not_a_record_set(
        self, tmp_path: Path, data_root: Path
    ) -> None:
        broken = tmp_path / "broken.json"
        broken.write_text("{}", encoding="utf-8")
        assert main(["ingest", str(broken)]) == EXIT_BAD_INPUT


class TestBuild:
    def test_builds_from_what_was_ingested(
        self, records: Path, data_root: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["ingest", str(records)])
        capsys.readouterr()

        assert main(["build"]) == EXIT_OK
        assert "outings" in capsys.readouterr().out.lower()

    def test_building_an_empty_library_is_not_an_error(self, data_root: Path) -> None:
        assert main(["build"]) == EXIT_OK


class TestReport:
    def test_prints_a_summary(
        self, records: Path, data_root: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["ingest", str(records)])
        main(["build"])
        capsys.readouterr()

        assert main(["report"]) == EXIT_OK
        assert "photographs" in capsys.readouterr().out.lower()

    def test_can_print_json_instead(
        self, records: Path, data_root: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Machine readable output is what makes the tool composable."""
        main(["ingest", str(records)])
        main(["build"])
        capsys.readouterr()

        assert main(["report", "--json"]) == EXIT_OK
        payload = json.loads(capsys.readouterr().out)
        assert payload["photographs"] == 6

    def test_reporting_on_an_empty_library_is_not_an_error(self, data_root: Path) -> None:
        assert main(["report"]) == EXIT_OK
