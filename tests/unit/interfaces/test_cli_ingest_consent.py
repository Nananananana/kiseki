"""The ingest command enforces the consent at the door."""

import json
import os
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqlitePhotoRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _run(tmp_path: Path, *arguments: str) -> int:
    return main(["--data-root", str(tmp_path), *arguments])


def _record(identifier: str, preference: bool, story: bool) -> dict[str, object]:
    return {
        "id": identifier,
        "captured_at": "2026-06-01T10:00:00+09:00",
        "location": None,
        "content_kind": "photo",
        "consent": {"use_for_preference": preference, "use_for_story": story},
    }


def _stored(tmp_path: Path) -> tuple:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    try:
        return SqlitePhotoRepository(connection).all()
    finally:
        connection.close()


class TestIngestConsent:
    def test_a_story_refusal_is_dropped_at_the_door(self, tmp_path: Path) -> None:
        document = {"records": [_record("sha256:a", True, False), _record("sha256:b", True, True)]}
        records = tmp_path / "records.json"
        records.write_text(json.dumps(document), encoding="utf-8")
        assert _run(tmp_path, "ingest", str(records)) == EXIT_OK
        stored = _stored(tmp_path)
        assert [photo.photo_id.value for photo in stored] == ["sha256:b"]

    def test_a_preference_refusal_is_carried(self, tmp_path: Path) -> None:
        document = {"records": [_record("sha256:a", False, True)]}
        records = tmp_path / "records.json"
        records.write_text(json.dumps(document), encoding="utf-8")
        assert _run(tmp_path, "ingest", str(records)) == EXIT_OK
        (photo,) = _stored(tmp_path)
        assert photo.use_for_preference is False
