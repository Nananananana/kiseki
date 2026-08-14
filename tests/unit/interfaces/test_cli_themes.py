"""The themes command reports what a run did.

On an empty database there are no labels, the run stays under the
minimum, and no model is touched, so this stays in CI.
"""

from pathlib import Path

import pytest

from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env beside the repo."""
    monkeypatch.chdir(tmp_path)


class TestThemesCommand:
    def test_answers_an_empty_database(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "themes"]) == EXIT_OK
        assert "themes" in capsys.readouterr().out
