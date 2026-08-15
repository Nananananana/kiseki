"""The view command writes one self-contained HTML file."""

import os
from pathlib import Path

import pytest
from kiseki.config.paths import resolve_paths
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _run(tmp_path: Path, *arguments: str) -> int:
    return main(["--data-root", str(tmp_path), *arguments])


class TestViewCommand:
    def test_writes_the_file_under_cache_by_default(self, tmp_path: Path) -> None:
        assert _run(tmp_path, "view") == EXIT_OK
        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        written = paths.cache_dir / "kiseki-view.html"
        assert written.is_file()
        page = written.read_text(encoding="utf-8")
        assert "<html" in page
        assert "https://" not in page

    def test_out_overrides_the_destination(self, tmp_path: Path) -> None:
        destination = tmp_path / "somewhere" / "view.html"
        assert _run(tmp_path, "view", "--out", str(destination)) == EXIT_OK
        assert destination.is_file()
