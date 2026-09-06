"""`kiseki tell` reads and does not keep, and --json carries the facts.

Every `tell` used to call `profile()` with its default, which keeps.
Telling is a reading (ADR-0070); the served route said `keep=False`
and the command line did not, so each story added a profile to the
history the trend is computed from.
"""

import json
import os
from pathlib import Path

import pytest
from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.adapters.sqlite.store import SqliteProfileRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.interfaces import cli
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cli,
        "_language_model",
        lambda args: FakeLanguageModel(answer=lambda system, prompt: "a story [F1]"),
    )


def _kept(tmp_path: Path) -> int:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    try:
        return len(SqliteProfileRepository(connection).history())
    finally:
        connection.close()


def test_telling_twice_keeps_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--data-root", str(tmp_path), "tell"]) == EXIT_OK
    assert main(["--data-root", str(tmp_path), "tell"]) == EXIT_OK
    assert _kept(tmp_path) == 0, "a story was kept as a profile reading"


def test_json_carries_the_story_and_its_facts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--data-root", str(tmp_path), "tell", "--json"]) == EXIT_OK
    out = capsys.readouterr().out
    document = json.loads(out[out.index("{") :])
    assert document["schema"] == "kiseki-tell"
    assert document["story"] == "a story [F1]"
    assert document["facts"][0]["id"] == "F1"


def test_the_story_is_still_printed_as_prose(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--data-root", str(tmp_path), "tell"]) == EXIT_OK
    assert "a story [F1]" in capsys.readouterr().out
