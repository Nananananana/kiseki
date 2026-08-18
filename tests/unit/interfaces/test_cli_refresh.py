"""One command runs the weekly routine, in the order that works."""

import os
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, REFRESH_STAGES, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def test_the_order_is_the_pipeline_s_order() -> None:
    assert REFRESH_STAGES == (
        "build",
        "caption",
        "singles",
        "screens",
        "subjects",
        "themes",
        "index",
        "profile",
    )


def test_a_dry_run_lists_the_stages_and_touches_no_model(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--data-root", str(tmp_path), "refresh", "--dry-run"]) == EXIT_OK
    out = capsys.readouterr().out
    for stage in REFRESH_STAGES:
        assert stage in out
    assert "doctor" in out
    assert "ingest" in out
