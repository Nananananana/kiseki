"""The places command reads journeys; without them it says so."""

import os
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def test_no_journeys_is_said_plainly(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--data-root", str(tmp_path), "places"]) == EXIT_OK
    assert "no places yet" in capsys.readouterr().out
