"""A version 1 database is migrated in place; anything unknown is refused.

The first real migration. The step is explicit rather than guessed at:
version 1 gains the thumbnail column and becomes version 2, and any
version this code does not know is still refused. See ADR-0018.
"""

import sqlite3
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SCHEMA_VERSION, SqlitePhotoRepository, connect

V1_TABLES = """
CREATE TABLE schema_version (version INTEGER NOT NULL);
CREATE TABLE photos (
    id           TEXT PRIMARY KEY,
    captured_at  TEXT NOT NULL,
    latitude     REAL,
    longitude    REAL
);
"""


def _version_one_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(V1_TABLES)
    connection.execute("INSERT INTO schema_version (version) VALUES (1)")
    connection.execute(
        "INSERT INTO photos (id, captured_at, latitude, longitude) VALUES (?, ?, ?, ?)",
        ("sha256:aa", "2026-05-03T10:00:00+09:00", 35.0, 135.0),
    )
    connection.commit()
    connection.close()


class TestMigration:
    def test_a_version_one_database_is_migrated_in_place(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        _version_one_database(path)

        connection = connect(path)
        try:
            stored = connection.execute("SELECT version FROM schema_version").fetchone()[0]
            assert stored == SCHEMA_VERSION
            migrated = SqlitePhotoRepository(connection).all()[0]
            assert migrated.photo_id.value == "sha256:aa"
            assert migrated.thumbnail_ref is None
        finally:
            connection.close()

    def test_an_unknown_version_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version (version) VALUES (99)")
        connection.commit()
        connection.close()

        with pytest.raises(ValueError):
            connect(path)
