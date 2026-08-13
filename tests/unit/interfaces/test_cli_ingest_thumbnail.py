"""Ingesting through the CLI carries the thumbnail reference into storage."""

import json
import os
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqlitePhotoRepository, connect
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


DOCUMENT = {
    "schema_version": "1.0",
    "records": [
        {
            "id": "sha256:" + "a" * 64,
            "captured_at": "2026-05-03T10:24:31+09:00",
            "location": {"lat": 35.0094, "lon": 135.6669},
            "location_source": "measured",
            "media_type": "image",
            "content_kind": "photo",
            "thumbnail_ref": "2026/05/aaaa.jpg",
            "owner": {"owner_id": "u1"},
            "consent": {"use_for_preference": True, "use_for_story": True},
        }
    ],
}


class TestIngestThumbnail:
    def test_the_reference_reaches_storage(self, tmp_path: Path) -> None:
        records = tmp_path / "photo-records.json"
        records.write_text(json.dumps(DOCUMENT), encoding="utf-8")

        assert main(["--data-root", str(tmp_path), "ingest", str(records)]) == EXIT_OK

        connection = connect(tmp_path / "db" / "kiseki.sqlite3")
        try:
            stored = SqlitePhotoRepository(connection).all()[0]
            assert stored.thumbnail_ref == "2026/05/aaaa.jpg"
        finally:
            connection.close()
