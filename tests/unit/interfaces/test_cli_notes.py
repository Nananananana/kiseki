"""The core reads what a note producer wrote."""

import json
import os
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqliteNoteReadingRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _write(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    path = tmp_path / "note-records.json"
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    return path


def _stored(tmp_path: Path):
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    return SqliteNoteReadingRepository(connect(paths.db_path)).all()


class TestNotesCommand:
    def test_readings_are_read(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        path = _write(
            tmp_path,
            [
                {
                    "owner": "me",
                    "platform": "notes",
                    "day": "2026-08-29",
                    "reference": "note:aaaa",
                    "category": "reading",
                    "labels": ["raft", "consensus"],
                },
                {
                    "owner": "me",
                    "platform": "notes",
                    "day": "2026-08-29",
                    "reference": "note:bbbb",
                    "category": "journal",
                    "labels": [],
                },
            ],
        )
        assert main(["--data-root", str(tmp_path), "notes", str(path)]) == EXIT_OK
        out = capsys.readouterr().out
        assert "readings read 2" in out
        readings = _stored(tmp_path)
        assert {reading.category for reading in readings} == {"reading", "journal"}

    def test_a_trail_is_kept(self, tmp_path: Path) -> None:
        """The same note on later days adds readings rather than replacing."""
        for day in ("2026-03-01", "2026-05-14", "2026-08-29"):
            path = _write(
                tmp_path,
                [
                    {
                        "owner": "me",
                        "platform": "notes",
                        "day": day,
                        "reference": "note:aaaa",
                        "category": "reading",
                        "labels": ["raft"],
                    }
                ],
            )
            assert main(["--data-root", str(tmp_path), "notes", str(path)]) == EXIT_OK
        assert len(_stored(tmp_path)) == 3

    def test_the_same_day_replaces(self, tmp_path: Path) -> None:
        for labels in (["raft"], ["paxos"]):
            path = _write(
                tmp_path,
                [
                    {
                        "owner": "me",
                        "platform": "notes",
                        "day": "2026-08-29",
                        "reference": "note:aaaa",
                        "category": "reading",
                        "labels": labels,
                    }
                ],
            )
            assert main(["--data-root", str(tmp_path), "notes", str(path)]) == EXIT_OK
        readings = _stored(tmp_path)
        assert len(readings) == 1
        assert readings[0].labels == ("paxos",)

    def test_a_sensitive_category_with_labels_is_refused(self, tmp_path: Path) -> None:
        """The producer promised not to send them; a core that tidied would hide it."""
        path = _write(
            tmp_path,
            [
                {
                    "owner": "me",
                    "platform": "notes",
                    "day": "2026-08-29",
                    "reference": "note:aaaa",
                    "category": "journal",
                    "labels": ["a bad day"],
                }
            ],
        )
        assert main(["--data-root", str(tmp_path), "notes", str(path)]) == EXIT_BAD_INPUT
        assert _stored(tmp_path) == ()

    def test_a_missing_file_is_said_plainly(self, tmp_path: Path) -> None:
        assert (
            main(["--data-root", str(tmp_path), "notes", str(tmp_path / "nope.json")])
            == EXIT_BAD_INPUT
        )
