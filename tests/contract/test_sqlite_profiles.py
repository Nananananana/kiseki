"""The SQLite profile repository must satisfy the same contract as the fake."""

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

from kiseki.adapters.sqlite.store import SqliteProfileRepository, connect
from profile_contract import ProfileRepositoryContract, build_profile


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = connect(tmp_path / "kiseki.sqlite3")
    yield handle
    handle.close()


class TestSqliteProfileRepository(ProfileRepositoryContract):
    @pytest.fixture
    def profiles(self, connection: sqlite3.Connection) -> SqliteProfileRepository:
        return SqliteProfileRepository(connection)


class TestProfilePersistence:
    """Behaviour specific to a database, which a fake cannot exercise."""

    def test_a_profile_survives_reopening(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        saved = build_profile(datetime(2026, 3, 1, 12, tzinfo=timezone.utc))

        first = connect(path)
        SqliteProfileRepository(first).save(saved)
        first.close()

        second = connect(path)
        try:
            assert SqliteProfileRepository(second).latest() == saved
        finally:
            second.close()

    def test_an_existing_database_gains_the_profiles_table(self, tmp_path: Path) -> None:
        """The table is additive: no schema version bump, no migration."""
        path = tmp_path / "kiseki.sqlite3"
        connect(path).close()
        reopened = connect(path)
        try:
            repository = SqliteProfileRepository(reopened)
            assert repository.latest() is None
        finally:
            reopened.close()
