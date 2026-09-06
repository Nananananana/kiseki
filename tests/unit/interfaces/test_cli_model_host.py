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


def test_llm_reports_keep_alive_and_timeout_from_this_process(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An orchestrator running one stage per process says `0` on the
    last job of the night; `llm` must show that it was heard."""
    monkeypatch.setenv("KISEKI_MODEL_KEEP_ALIVE", "0")
    monkeypatch.setenv("KISEKI_MODEL_TIMEOUT_SECONDS", "45")
    assert main(["--data-root", str(tmp_path), "llm"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "keep_alive      0" in out
    assert "timeout         45s" in out


def test_the_adapters_are_built_with_what_this_process_said(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`llm` printing a value is not the same as a captioner receiving it.
    The four constructors passed only model and host until the settings
    grew keep_alive and timeout; this holds the wiring, not the print."""
    from kiseki.interfaces.cli import _captioner, _embedder, _language_model, _screen_reader

    monkeypatch.setenv("KISEKI_MODEL_KEEP_ALIVE", "0")
    monkeypatch.setenv("KISEKI_MODEL_TIMEOUT_SECONDS", "45")
    args = build_parser().parse_args(["llm"])
    for build in (_captioner, _language_model, _embedder, _screen_reader):
        adapter = build(args)
        assert adapter._keep_alive == "0", build.__name__
