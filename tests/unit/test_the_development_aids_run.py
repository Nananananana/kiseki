"""The two development aids still run, on a document already here.

`tools/journeys.py` raised `AttributeError` on every document it was
given, from #15 until #355 -- the refactor that turned `assemble_outings`
into a function returning a tuple left the tool calling `.outings` on
it, and the tool has no caller in CI, so nothing said anything for the
rest of the repository's life. The type checker found it the first
time it was pointed at `tools/`, and now covers it.

The type checker is not enough on its own. It cannot see a fixture
that moved, a flag that was renamed, or a loader that started
expecting a different document -- all of which are how a script that
reads a real document actually breaks. This runs both aids
end to end.

Against `tests/fixtures/photo_record/valid_full.json`, which is on
disk already, because the rule this repository keeps is: **delete what
needs new machinery to check, keep what can be checked against
something already there.** A fixture of one photograph makes no stop
and no outing, and that is enough -- the line that was broken for two
years is the line that prints how many outings there were.
"""

import runpy
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
DOCUMENT = REPO_ROOT / "tests" / "fixtures" / "photo_record" / "valid_full.json"

AIDS = ("journeys.py", "profile.py")
"""Every script under `tools/` that reads a PhotoRecord document.
`check_packaging.py` is left out: it builds five wheels and installs
them, which is a minute of CI, and it is a gate of its own already."""


def run(script: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", [script, str(DOCUMENT)])
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(str(REPO_ROOT / "tools" / script), run_name="__main__")
    assert raised.value.code == 0, f"tools/{script} refused a document this repository ships"


def test_the_document_it_runs_against_is_there() -> None:
    """A test whose fixture has moved passes by not running."""
    assert DOCUMENT.is_file(), f"the fixture these aids are run against is gone: {DOCUMENT}"


@pytest.mark.parametrize("script", AIDS)
def test_it_runs_to_the_end(
    script: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run(script, monkeypatch)
    assert capsys.readouterr().out.strip(), f"tools/{script} ran and said nothing"


def test_every_aid_named_here_exists() -> None:
    missing = [name for name in AIDS if not (REPO_ROOT / "tools" / name).is_file()]
    assert not missing, f"named here but not in tools/: {missing}"


def test_the_outing_count_is_reached() -> None:
    """The line that was broken, named. A tool that failed earlier for
    another reason would pass the test above by exiting 0 sooner."""
    monkeypatch = pytest.MonkeyPatch()
    try:
        import io
        from contextlib import redirect_stdout

        captured = io.StringIO()
        monkeypatch.setattr(sys, "argv", ["journeys.py", str(DOCUMENT)])
        with redirect_stdout(captured), pytest.raises(SystemExit):
            runpy.run_path(str(REPO_ROOT / "tools" / "journeys.py"), run_name="__main__")
    finally:
        monkeypatch.undo()
    assert "outings" in captured.getvalue()
