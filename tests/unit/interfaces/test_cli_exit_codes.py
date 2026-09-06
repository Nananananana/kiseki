"""Exit codes tell refused from unavailable from timed out.

Two codes used to cover everything, 0 and 2. A refused model and an
unavailable one both left as 2, and a captioning run that paused on an
outage left as 0 -- so an orchestrator writing `refused` / `unavailable`
/ `timed_out` into a ledger, and never retrying the first, could not.
"""

import os
from pathlib import Path

import pytest
from kiseki.application.captioning import CaptionRunReport
from kiseki.interfaces import cli
from kiseki.interfaces.cli import (
    EXIT_MODEL_REFUSED,
    EXIT_MODEL_TIMED_OUT,
    EXIT_MODEL_UNAVAILABLE,
    EXIT_OK,
    main,
)
from kiseki.ports.models import ModelRefusedError, ModelTimedOutError, ModelUnavailableError


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


class _Failing:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def complete(self, system: str, prompts: list[str]) -> list:
        raise self._error


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (ModelRefusedError("declined"), EXIT_MODEL_REFUSED),
        (ModelUnavailableError("down"), EXIT_MODEL_UNAVAILABLE),
        (ModelTimedOutError("slow"), EXIT_MODEL_TIMED_OUT),
    ],
    ids=["refused", "unavailable", "timed_out"],
)
def test_llm_check_leaves_with_the_code_for_what_happened(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
    code: int,
) -> None:
    monkeypatch.setattr(cli, "_language_model", lambda args: _Failing(error))
    assert main(["--data-root", str(tmp_path), "llm", "--check"]) == code
    assert "reachable       no" in capsys.readouterr().out


def test_a_paused_captioning_run_is_unavailable_not_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The run is resumable and says so; the code says the model was the
    reason it stopped, so the next night's job knows to come back."""
    paused = CaptionRunReport(3, 0, 0, 0, True)
    monkeypatch.setattr(cli, "run_captioning", lambda **kwargs: paused)
    monkeypatch.setattr(cli, "_captioner", lambda args: object())
    assert main(["--data-root", str(tmp_path), "caption"]) == EXIT_MODEL_UNAVAILABLE
    assert "paused" in capsys.readouterr().out


def test_a_finished_captioning_run_is_still_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    done = CaptionRunReport(3, 0, 0, 0, False)
    monkeypatch.setattr(cli, "run_captioning", lambda **kwargs: done)
    monkeypatch.setattr(cli, "_captioner", lambda args: object())
    assert main(["--data-root", str(tmp_path), "caption"]) == EXIT_OK
