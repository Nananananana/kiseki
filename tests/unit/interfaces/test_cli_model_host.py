"""`--model-host` reaches the settings, and outranks the environment.

Found while adding `--parallel` beside it: nothing anywhere tested
`--model-host`, so `llm` had quietly grown its own way of reading it
that knew nothing about any later flag. The flag is the top layer of
the five, and both the commands that use a model and the one that
reports on it must see the same value.
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
    assert build_parser().parse_args(["llm"]).model_host is None
    given = build_parser().parse_args(["--model-host", "http://127.0.0.1:11434", "llm"])
    assert given.model_host == "http://127.0.0.1:11434"


def test_llm_reports_the_host_the_flag_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(["--data-root", str(tmp_path), "--model-host", "http://127.0.0.1:11435", "llm"])
        == EXIT_OK
    )
    assert "host            http://127.0.0.1:11435" in capsys.readouterr().out


def test_the_flag_outranks_the_environment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KISEKI_MODEL_HOST", "http://127.0.0.1:11436")
    assert (
        main(["--data-root", str(tmp_path), "--model-host", "http://127.0.0.1:11437", "llm"])
        == EXIT_OK
    )
    out = capsys.readouterr().out
    assert "11437" in out
    assert "11436" not in out
