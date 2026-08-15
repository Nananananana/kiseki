"""Both repository implementations honour the shared contract."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from kiseki.adapters.fake.screens import FakeScreenshotReadingRepository
from kiseki.adapters.sqlite.store import SqliteScreenshotReadingRepository, connect
from screen_reading_contract import ScreenshotReadingRepositoryContract


class TestFakeScreenshotReadingRepository(ScreenshotReadingRepositoryContract):
    @pytest.fixture
    def readings(self) -> FakeScreenshotReadingRepository:
        return FakeScreenshotReadingRepository()


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = connect(tmp_path / "kiseki.sqlite3")
    yield handle
    handle.close()


class TestSqliteScreenshotReadingRepository(ScreenshotReadingRepositoryContract):
    @pytest.fixture
    def readings(self, connection: sqlite3.Connection) -> SqliteScreenshotReadingRepository:
        return SqliteScreenshotReadingRepository(connection)
