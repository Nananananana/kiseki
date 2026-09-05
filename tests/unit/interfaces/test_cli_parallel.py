"""`--parallel` is a model setting on the command line, and refresh carries it.

`refresh` re-parses each stage with only `--data-root`, so a flag on
`caption` alone would never reach the weekly routine. It is a top-level
flag, resolved through the same five layers as the model host, and
forwarded by `refresh` the way `--data-root` is.
"""

import os
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, build_parser, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def test_the_flag_is_parsed_and_absent_by_default() -> None:
    assert build_parser().parse_args(["caption"]).parallel is None
    assert build_parser().parse_args(["--parallel", "4", "caption"]).parallel == 4


def test_a_word_is_refused_at_the_door() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--parallel", "four", "caption"])


def test_llm_reports_what_is_in_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KISEKI_MODEL_PARALLEL", "3")
    assert main(["--data-root", str(tmp_path), "llm"]) == EXIT_OK
    assert "parallel        3 call(s)" in capsys.readouterr().out


def test_the_command_line_outranks_the_environment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KISEKI_MODEL_PARALLEL", "3")
    assert main(["--data-root", str(tmp_path), "--parallel", "2", "llm"]) == EXIT_OK
    assert "parallel        2 call(s)" in capsys.readouterr().out


def test_refresh_dry_run_still_lists_the_stages(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(["--data-root", str(tmp_path), "--parallel", "2", "refresh", "--dry-run"]) == EXIT_OK
    )
    assert "kiseki caption" in capsys.readouterr().out
