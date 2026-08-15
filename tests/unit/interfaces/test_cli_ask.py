"""The ask command answers safely on an empty database.

With nothing indexed there is no retrieval and no model call, so this
stays in CI.
"""

from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env beside the repo."""
    monkeypatch.chdir(tmp_path)


class TestAskCommand:
    def test_answers_an_empty_database(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "ask", "ramen"]) == EXIT_OK
        assert "no evidence" in capsys.readouterr().out

    def test_answers_the_contract_as_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "ask", "--json", "ramen"]) == EXIT_OK
        out = capsys.readouterr().out
        assert '"question"' in out
        assert '"confidence"' in out
