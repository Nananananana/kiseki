"""--near wants lat,lon; anything else is refused before any work."""

import os
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_BAD_INPUT, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def test_a_bad_near_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--data-root", str(tmp_path), "ask", "ramen ?", "--near", "osaka"])
    assert caught.value.code == EXIT_BAD_INPUT
