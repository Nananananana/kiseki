"""The tour visits everything, and says what each stop answers."""

import contextlib
import io
import os
from dataclasses import dataclass
from pathlib import Path

import pytest
from kiseki.application.tour import MODEL_STAGES, TOUR, WALKED
from kiseki.interfaces.cli import EXIT_OK, build_parser, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _known_commands() -> set[str]:
    parser = build_parser()
    known: set[str] = set()
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if choices:
            known.update(str(choice) for choice in choices)
    return known


def test_every_stop_names_a_real_command() -> None:
    """A tour of commands that do not exist is a tour of nothing."""
    known = _known_commands()
    for stop in TOUR:
        assert stop.name in known, stop.name


def test_the_tour_leaves_no_command_unmentioned() -> None:
    """If a command exists and the tour does not name it, the tour is stale."""
    named = {stop.name for stop in TOUR}
    missing = sorted(_known_commands() - named)
    assert missing == [], missing


def test_every_stop_says_what_it_answers() -> None:
    for stop in TOUR:
        assert stop.says
        assert not stop.says.endswith(".")


def test_the_model_stages_are_described_rather_than_run() -> None:
    assert "ask" in MODEL_STAGES
    assert "tell" in MODEL_STAGES
    assert "profile" not in MODEL_STAGES
    assert all(stop.runs for stop in WALKED)


@dataclass(frozen=True)
class FullTour:
    """One `demo --full --write`, shared by every test that reads it.

    The three tests below used to run the whole tour each -- 45 of the
    suite's 91 seconds, for one run's worth of information. They ask
    different questions of the same output, so the output is made once.
    """

    printed: str
    written: str
    sandbox: Path
    cwd_after: Path
    environment_after: dict[str, str]


@pytest.fixture(scope="module")
def full_tour(tmp_path_factory: pytest.TempPathFactory) -> FullTour:
    root = tmp_path_factory.mktemp("tour")
    sandbox = root / "sandbox"
    document = root / "tour.md"
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        del os.environ[key]
    os.environ["KISEKI_TOUR_CANARY"] = "still here"
    before = Path.cwd()
    os.chdir(root)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            code = main(["demo", "--full", "--out", str(sandbox), "--write", str(document)])
        cwd_after = Path.cwd()
        environment_after = {k: v for k, v in os.environ.items() if k.startswith("KISEKI_")}
    finally:
        os.chdir(before)
        os.environ.pop("KISEKI_TOUR_CANARY", None)
    assert code == EXIT_OK
    return FullTour(
        printed=buffer.getvalue(),
        written=document.read_text(encoding="utf-8"),
        sandbox=sandbox,
        cwd_after=cwd_after,
        environment_after=environment_after,
    )


def test_the_full_tour_runs_and_says_what_it_visited(full_tour: FullTour) -> None:
    for name in ("places", "trips", "suggest", "privacy", "doctor"):
        assert name in full_tour.printed
    assert "needs a model" in full_tour.printed or "not run here" in full_tour.printed


def test_the_full_tour_sweeps_up(full_tour: FullTour) -> None:
    assert not full_tour.sandbox.exists()


def test_it_can_be_kept_as_a_document(full_tour: FullTour) -> None:
    assert full_tour.written.startswith("# ")
    assert "## places" in full_tour.written
    assert "```" in full_tour.written


def test_the_tour_puts_the_process_back_where_it_found_it(full_tour: FullTour) -> None:
    """`_run_quietly` set KISEKI_* aside and moved into the sandbox, and
    put neither back. After a tour the process sat inside a directory
    about to be deleted -- the reason `_sweep` retries its rmtree --
    with the owner's environment gone for the rest of the run."""
    assert full_tour.cwd_after != full_tour.sandbox
    assert full_tour.cwd_after.exists()
    assert full_tour.environment_after.get("KISEKI_TOUR_CANARY") == "still here", (
        "the tour deleted the owner's KISEKI_* variables and never restored them"
    )


def test_the_short_demo_still_works(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demo", "--out", str(tmp_path / "sandbox")]) == EXIT_OK
    assert "a synthetic library" in capsys.readouterr().out
