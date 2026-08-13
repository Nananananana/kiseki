"""The SQLite implementation must satisfy the same contract as the fakes."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from conftest import observation, outing, stop
from kiseki.adapters.sqlite.store import (
    SqliteAnchorRepository,
    SqliteOutingRepository,
    SqlitePhotoRepository,
    connect,
)
from repository_contract import (
    AnchorRepositoryContract,
    OutingRepositoryContract,
    PhotoRepositoryContract,
)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = connect(tmp_path / "nested" / "kiseki.sqlite3")
    yield handle
    handle.close()


class TestSqlitePhotoRepository(PhotoRepositoryContract):
    @pytest.fixture
    def photos(self, connection: sqlite3.Connection) -> SqlitePhotoRepository:
        return SqlitePhotoRepository(connection)


class TestSqliteOutingRepository(OutingRepositoryContract):
    @pytest.fixture
    def outings(self, connection: sqlite3.Connection) -> SqliteOutingRepository:
        return SqliteOutingRepository(connection)


class TestSqliteAnchorRepository(AnchorRepositoryContract):
    @pytest.fixture
    def anchors(self, connection: sqlite3.Connection) -> SqliteAnchorRepository:
        return SqliteAnchorRepository(connection)


class TestPersistence:
    """Behaviour specific to a database, which a fake cannot exercise."""

    def test_creates_the_directory_it_is_given(self, tmp_path: Path) -> None:
        path = tmp_path / "deeply" / "nested" / "kiseki.sqlite3"
        connect(path).close()
        assert path.exists()

    def test_data_survives_reopening(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        first = connect(path)
        SqlitePhotoRepository(first).save_all([observation(0, 9), observation(1, 10)])
        first.close()

        second = connect(path)
        assert SqlitePhotoRepository(second).count() == 2
        second.close()

    def test_replacing_outings_removes_their_stops(
        self, connection: sqlite3.Connection
    ) -> None:
        """Orphaned rows would silently inflate every later query."""
        outings = SqliteOutingRepository(connection)
        outings.replace_all([outing(stop("a", 9, 11, 35.0, 135.0))])
        outings.replace_all([])

        assert connection.execute("SELECT COUNT(*) FROM stops").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM stop_photos").fetchone()[0] == 0

    def test_refuses_a_database_from_another_schema(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        connect(path).close()

        handle = sqlite3.connect(path)
        handle.execute("UPDATE schema_version SET version = 99")
        handle.commit()
        handle.close()

        with pytest.raises(ValueError, match="schema"):
            connect(path)
