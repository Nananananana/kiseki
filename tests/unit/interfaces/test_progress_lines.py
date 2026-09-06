"""--progress jsonl: one line per window on stderr, counts and nothing else."""

import io
import json
import os
from pathlib import Path

import pytest
from kiseki.application.captioning import CaptionRunReport
from kiseki.application.estimating import Stage
from kiseki.interfaces import cli
from kiseki.interfaces.cli import EXIT_OK, build_parser, main
from kiseki.interfaces.progress import json_lines


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def test_a_report_is_one_json_line_with_the_estimator_s_total() -> None:
    out = io.StringIO()
    report = json_lines("caption", (Stage("stay captions", 360, None, "a stay"),), stream=out)
    report(12, None)
    lines = out.getvalue().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"stage": "caption", "done": 12, "total": 360, "resumable": True}


def test_a_loop_that_knows_its_own_total_wins() -> None:
    out = io.StringIO()
    report = json_lines("index", (), stream=out)
    report(32, 1000)
    assert json.loads(out.getvalue())["total"] == 1000


def test_nothing_but_counts_is_on_a_line() -> None:
    """An orchestrator's screen gets a bar; it does not get a caption or
    a photograph identifier, and the shape says so."""
    out = io.StringIO()
    json_lines("caption", (), stream=out)(1, 2)
    assert set(json.loads(out.getvalue())) == {"stage", "done", "total", "resumable"}


def test_the_flag_is_parsed_and_off_by_default() -> None:
    assert build_parser().parse_args(["caption"]).progress is None
    assert build_parser().parse_args(["--progress", "jsonl", "caption"]).progress == "jsonl"


def test_caption_wires_the_reporter_to_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The loop is faked; what is under test is that the command hands it
    a reporter named for the stage, and that the line lands on stderr."""
    seen: list[object] = []

    def fake_run(**kwargs: object) -> CaptionRunReport:
        on_progress = kwargs["on_progress"]
        seen.append(on_progress)
        assert callable(on_progress)
        on_progress(3, None)
        return CaptionRunReport(3, 0, 0, 0, False)

    monkeypatch.setattr(cli, "run_captioning", fake_run)
    monkeypatch.setattr(cli, "_captioner", lambda args: object())
    assert main(["--data-root", str(tmp_path), "--progress", "jsonl", "caption"]) == EXIT_OK
    captured = capsys.readouterr()
    line = json.loads(captured.err.strip().splitlines()[-1])
    assert line["stage"] == "caption"
    assert line["done"] == 3
    assert isinstance(line["total"], int)
    assert "{" not in captured.out, "a progress line leaked into the human report"


def test_without_the_flag_no_reporter_is_handed_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    handed: list[object] = []

    def fake_run(**kwargs: object) -> CaptionRunReport:
        handed.append(kwargs["on_progress"])
        return CaptionRunReport(0, 0, 0, 0, False)

    monkeypatch.setattr(cli, "run_captioning", fake_run)
    monkeypatch.setattr(cli, "_captioner", lambda args: object())
    assert main(["--data-root", str(tmp_path), "caption"]) == EXIT_OK
    assert handed == [None]


def test_refresh_forwards_the_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(["--data-root", str(tmp_path), "--progress", "jsonl", "refresh", "--dry-run"])
        == EXIT_OK
    )
