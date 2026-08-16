"""A narrow console encoding degrades a name; it never crashes."""

import io
import sys
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env beside the repo."""
    monkeypatch.chdir(tmp_path)


def test_the_console_encoding_cannot_crash_the_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    buffer = io.BytesIO()
    wrapper = io.TextIOWrapper(buffer, encoding="cp932")
    monkeypatch.setattr(sys, "stdout", wrapper)
    assert main(["--data-root", str(tmp_path), "paths"]) == EXIT_OK
    print("\u014csaka")
    wrapper.flush()
    assert b"?saka" in buffer.getvalue()
