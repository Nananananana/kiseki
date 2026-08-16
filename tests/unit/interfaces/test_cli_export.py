"""The export is a deliberate act: a command, never an endpoint."""

import json
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env beside the repo."""
    monkeypatch.chdir(tmp_path)


class TestExportCommand:
    def test_prints_the_schema(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["--data-root", str(tmp_path), "export"]) == EXIT_OK
        document = json.loads(capsys.readouterr().out)
        assert document["schema"] == "kiseki-interest-export"
        assert document["interests"] == []

    def test_writes_a_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        target = tmp_path / "out" / "interests.json"
        assert main(["--data-root", str(tmp_path), "export", "--out", str(target)]) == EXIT_OK
        assert "exported" in capsys.readouterr().out
        document = json.loads(target.read_text(encoding="utf-8"))
        assert document["version"] == 1
