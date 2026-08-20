"""Schema version 3: photos gain a content kind.

The first chained migration -- a version 1 database must walk
1 -> 2 -> 3 on connect, each step explicit, and an unknown version is
still refused rather than guessed at (ADR-0018, ADR-0028).
"""

import sqlite3
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import connect

V2_TABLES = """
CREATE TABLE schema_version (version INTEGER NOT NULL);
CREATE TABLE photos (
    id            TEXT PRIMARY KEY,
    captured_at   TEXT NOT NULL,
    latitude      REAL,
    longitude     REAL,
    thumbnail_ref TEXT
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


def _version(connection: sqlite3.Connection) -> int:
    stored: int = connection.execute("SELECT version FROM schema_version").fetchone()[0]
    return stored


class TestSchemaV3:
    def test_a_version_2_database_gains_the_content_kind_column(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        _old_database(path, V2_TABLES, 2)
        connection = connect(path)
        try:
            assert "content_kind" in _columns(connection)
            assert _version(connection) == 6
        finally:
            connection.close()

    def test_a_version_1_database_walks_both_migrations(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        _old_database(path, V1_TABLES, 1)
        connection = connect(path)
        try:
            assert "thumbnail_ref" in _columns(connection)
            assert "content_kind" in _columns(connection)
            assert _version(connection) == 6
        finally:
            connection.close()

    def test_an_unknown_version_is_still_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        _old_database(path, V2_TABLES, 99)
        with pytest.raises(ValueError):
            connect(path)
