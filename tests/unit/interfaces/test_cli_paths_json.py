"""`kiseki paths --json`: can this profile be deleted by deleting one folder?

An orchestrator running several people on one machine separates them by
data root, and wants to tell a person *delete this folder and it is all
gone*. It cannot say that by reading seven lines: this library's own
development root is on `F:` with the database on `C:`, and deleting the
folder would leave the database behind.
"""

import json
import os
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _document(tmp_path: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> dict:
    assert main(["--data-root", str(tmp_path), *extra, "paths", "--json"]) == EXIT_OK
    out = capsys.readouterr().out
    return json.loads(out[out.index("{") :])


def test_it_names_itself_and_every_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    document = _document(tmp_path, capsys)
    assert document["schema"] == "kiseki-paths"
    for name in (
        "data_root",
        "records_dir",
        "thumbs_dir",
        "db_path",
        "cache_dir",
        "log_dir",
        "gazetteer_path",
    ):
        assert name in document, name


def test_a_root_that_holds_everything_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Empty `outside_root` is the answer to *is one deletion enough?*"""
    assert _document(tmp_path, capsys)["outside_root"] == []


def test_a_path_outside_the_root_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real configuration this exists for, and the trap in setting it up.

    Both the root and the database must be named in the *same* layer.
    Passing `--data-root` on the command line sets aside a weaker
    `KISEKI_DB_PATH` entirely -- which is the protection `set_aside`
    exists to give, and which made the first version of this test pass
    while proving nothing.
    """
    elsewhere = tmp_path.parent / "elsewhere" / "kiseki.sqlite3"
    monkeypatch.setenv("KISEKI_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("KISEKI_DB_PATH", str(elsewhere))
    assert main(["paths", "--json"]) == EXIT_OK
    out = capsys.readouterr().out
    document = json.loads(out[out.index("{") :])
    assert document["outside_root"] == ["db_path"]
    assert document["db_path"] == str(elsewhere)


def test_a_weaker_path_is_set_aside_rather_than_left_outside(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--data-root` outranks the environment, so the database follows the
    root and nothing is outside it. `set_aside` says what was overruled."""
    monkeypatch.setenv("KISEKI_DB_PATH", str(tmp_path.parent / "ignored.sqlite3"))
    document = _document(tmp_path, capsys)
    assert document["outside_root"] == []
    assert document["set_aside"] == ["db_path"]


def test_without_json_it_still_prints_for_a_person(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--data-root", str(tmp_path), "paths"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "data_root" in out
    assert "{" not in out
