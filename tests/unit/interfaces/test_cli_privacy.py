"""The privacy command reports, and promises only what code enforces."""

from pathlib import Path

import json

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env beside the repo."""
    monkeypatch.chdir(tmp_path)


class TestPrivacyCommand:
    def test_reports_an_empty_database(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "privacy"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "photographs" in out
        assert "never stored" in out
        assert "screenshot text" in out

    def test_json_carries_the_counts(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "privacy", "--json"]) == EXIT_OK
        payload = json.loads(capsys.readouterr().out)
        assert payload["photographs"] == 0
        assert "never_stored" in payload
