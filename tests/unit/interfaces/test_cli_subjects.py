"""The subjects command reports what a run did.

On an empty database the run does nothing and never reaches a model,
so this stays in CI.
"""

from pathlib import Path

import pytest

from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env beside the repo."""
    monkeypatch.chdir(tmp_path)


class TestSubjectsCommand:
    def test_answers_an_empty_database(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "subjects"]) == EXIT_OK
        assert "extracted" in capsys.readouterr().out
