"""The narration check reaches the reader, in the words it was given."""

import os
from pathlib import Path

import pytest
from kiseki.application.narration_validation import NarrationDefect
from kiseki.interfaces.cli import narration_checks


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


FACTS = ("161 distinct places were visited; 82% were never returned to.",)


def test_a_supported_story_prints_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    narration_checks("161 places, and 82% never again [F1]", FACTS)
    assert capsys.readouterr().out == ""


def test_a_defect_is_printed_beside_the_story(
    capsys: pytest.CaptureFixture[str],
) -> None:
    narration_checks("Only 18% were revisited [F1]", FACTS)
    out = capsys.readouterr().out
    assert NarrationDefect.UNSUPPORTED_NUMBER.value in out
    assert "check" in out


def test_every_defect_is_named(capsys: pytest.CaptureFixture[str]) -> None:
    narration_checks("Only 18% were revisited", FACTS)
    out = capsys.readouterr().out
    assert NarrationDefect.UNCITED.value in out
    assert NarrationDefect.UNSUPPORTED_NUMBER.value in out
