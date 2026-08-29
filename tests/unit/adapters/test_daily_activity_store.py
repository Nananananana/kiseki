"""Daily activity is stored beside the photographs, and touches none of them."""

from datetime import date
from pathlib import Path

from kiseki.adapters.sqlite.store import (
    SCHEMA_VERSION,
    SqliteDailyActivityRepository,
    SqlitePhotoRepository,
    connect,
)
from kiseki.domain.activity.daily import DailyActivity


def test_the_schema_is_at_six(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    stored = connection.execute("SELECT version FROM schema_version").fetchone()
    assert stored[0] == SCHEMA_VERSION == 8


def test_a_day_survives_the_round_trip(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteDailyActivityRepository(connection)
    repository.save_all(
        [
            DailyActivity(day=date(2026, 8, 18), steps=6000, distance_m=4200.0),
            DailyActivity(day=date(2026, 8, 19), steps=9000, floors=8),
        ]
    )
    days = repository.all()
    assert [day.day.isoformat() for day in days] == ["2026-08-18", "2026-08-19"]
    assert days[0].distance_m == 4200.0
    assert days[1].floors == 8
    assert days[1].distance_m is None


def test_the_same_day_twice_is_one_day(tmp_path: Path) -> None:
    """An export run twice replaces rather than doubles."""
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteDailyActivityRepository(connection)
    repository.save_all([DailyActivity(day=date(2026, 8, 19), steps=6000)])
    repository.save_all([DailyActivity(day=date(2026, 8, 19), steps=9000)])
    days = repository.all()
    assert len(days) == 1
    assert days[0].steps == 9000


def test_a_library_without_activity_is_empty_rather_than_broken(
    tmp_path: Path,
) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    assert SqliteDailyActivityRepository(connection).all() == ()
    assert SqliteDailyActivityRepository(connection).count() == 0


def test_a_version_five_database_gains_the_table(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "legacy.sqlite3"
    legacy = sqlite3.connect(path)
    legacy.executescript(
        "CREATE TABLE schema_version (version INTEGER NOT NULL);"
        " CREATE TABLE photos ("
        " id TEXT PRIMARY KEY, captured_at TEXT NOT NULL, latitude REAL,"
        " longitude REAL, thumbnail_ref TEXT, content_kind TEXT,"
        " use_for_preference INTEGER);"
    )
    legacy.execute("INSERT INTO schema_version (version) VALUES (5)")
    legacy.commit()
    legacy.close()

    connection = connect(path)
    stored = connection.execute("SELECT version FROM schema_version").fetchone()
    # The walk does not stop at six: a database from v5 arrives at the
    # current version, gaining each table on the way.
    assert stored[0] == 8
    assert SqliteDailyActivityRepository(connection).all() == ()
    assert SqlitePhotoRepository(connection).all() == ()
