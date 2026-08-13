"""The profile command reads the measures as interests and prints them."""

import json
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


def _run(tmp_path: Path, *arguments: str) -> int:
    return main(["--data-root", str(tmp_path), *arguments])


class TestProfileCommand:
    def test_answers_an_empty_database(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert _run(tmp_path, "profile") == EXIT_OK
        assert "interests" in capsys.readouterr().out

    def test_json_is_machine_readable(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert _run(tmp_path, "profile", "--json") == EXIT_OK
        payload = json.loads(capsys.readouterr().out)
        assert payload["interests"] == []
        assert "generated_at" in payload
