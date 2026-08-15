"""Schema version 4: photos gain the preference consent."""

import sqlite3
from pathlib import Path

from kiseki.adapters.sqlite.store import connect

V3_TABLES = """
CREATE TABLE schema_version (version INTEGER NOT NULL);
CREATE TABLE photos (
    id            TEXT PRIMARY KEY,
    captured_at   TEXT NOT NULL,
    latitude      REAL,
    longitude     REAL,
    thumbnail_ref TEXT,
    content_kind  TEXT
);
"""

V1_TABLES = """
CREATE TABLE schema_version (version INTEGER NOT NULL);
CREATE TABLE photos (
    id          TEXT PRIMARY KEY,
    captured_at TEXT NOT NULL,
    latitude    REAL,
    longitude   REAL
);
"""


def _old_database(path: Path, tables: str, version: int) -> None:
    raw = sqlite3.connect(path)
    raw.executescript(tables)
    raw.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
    raw.commit()
    raw.close()


def _columns(connection: sqlite3.Connection) -> list[str]:
    return [row[1] for row in connection.execute("PRAGMA table_info(photos)")]


class TestSchemaV4:
    def test_a_version_3_database_gains_the_consent_column(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        _old_database(path, V3_TABLES, 3)
        connection = connect(path)
        try:
            assert "use_for_preference" in _columns(connection)
            stored: int = connection.execute("SELECT version FROM schema_version").fetchone()[0]
            assert stored == 4
        finally:
            connection.close()

    def test_a_version_1_database_walks_every_migration(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        _old_database(path, V1_TABLES, 1)
        connection = connect(path)
        try:
            columns = _columns(connection)
            assert "thumbnail_ref" in columns
            assert "content_kind" in columns
            assert "use_for_preference" in columns
        finally:
            connection.close()
