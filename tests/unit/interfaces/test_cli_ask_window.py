"""Explicit --since/--until reach the ask command safely."""

from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env beside the repo."""
    monkeypatch.chdir(tmp_path)


class TestAskWindow:
    def test_iso_dates_are_accepted(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "--data-root",
                str(tmp_path),
                "ask",
                "--since",
                "2025-01-01",
                "--until",
                "2025-12-31",
                "ramen",
            ]
        )
        assert code == EXIT_OK
        assert "no evidence" in capsys.readouterr().out

    def test_a_bad_date_is_refused(self, tmp_path: Path) -> None:
        code = main(["--data-root", str(tmp_path), "ask", "--since", "not-a-date", "ramen"])
        assert code == EXIT_BAD_INPUT
