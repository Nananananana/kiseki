"""The tour visits everything, and says what each stop answers."""

import os
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


def test_the_full_tour_runs_and_says_what_it_visited(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["demo", "--full", "--out", str(tmp_path / "sandbox")]) == EXIT_OK
    out = capsys.readouterr().out
    for name in ("places", "trips", "suggest", "privacy", "doctor"):
        assert name in out
    assert "needs a model" in out or "not run here" in out


def test_the_full_tour_sweeps_up(tmp_path: Path) -> None:
    target = tmp_path / "sandbox"
    assert main(["demo", "--full", "--out", str(target)]) == EXIT_OK
    assert not target.exists()


def test_it_can_be_kept_as_a_document(tmp_path: Path) -> None:
    target = tmp_path / "sandbox"
    document = tmp_path / "tour.md"
    assert main(["demo", "--full", "--out", str(target), "--write", str(document)]) == EXIT_OK
    written = document.read_text(encoding="utf-8")
    assert written.startswith("# ")
    assert "## places" in written
    assert "```" in written


def test_the_short_demo_still_works(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demo", "--out", str(tmp_path / "sandbox")]) == EXIT_OK
    assert "a synthetic library" in capsys.readouterr().out
