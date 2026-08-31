"""Note readings are stored beside everything else, and touch none of it."""

from datetime import UTC, date, datetime
from pathlib import Path

from kiseki.adapters.sqlite.store import (
    SCHEMA_VERSION,
    SqliteNoteReadingRepository,
    SqlitePhotoRepository,
    connect,
)
from kiseki.domain.note.reading import NoteReading

WHEN = datetime(2026, 8, 29, 12, tzinfo=UTC)


def _reading(reference: str, category: str = "reading", labels: tuple[str, ...] = ("raft",)):
    return NoteReading(
        reference=reference,
        day=date(2026, 8, 29),
        category=category,
        labels=labels,
        model="demo",
        created_at=WHEN,
    )


def test_the_schema_is_at_seven(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    stored = connection.execute("SELECT version FROM schema_version").fetchone()
    assert stored[0] == SCHEMA_VERSION


def test_a_reading_survives_the_round_trip(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteNoteReadingRepository(connection)
    repository.save(_reading("note:aaaa"))
    repository.save(_reading("note:bbbb", category="journal", labels=()))
    readings = repository.all()
    assert [reading.reference for reading in readings] == ["note:aaaa", "note:bbbb"]
    assert readings[0].labels == ("raft",)
    assert readings[1].category == "journal"
    assert readings[1].labels == ()


def test_the_same_note_twice_is_one_reading(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteNoteReadingRepository(connection)
    repository.save(_reading("note:aaaa", labels=("raft",)))
    repository.save(_reading("note:aaaa", labels=("paxos",)))
    readings = repository.all()
    assert len(readings) == 1
    assert readings[0].labels == ("paxos",)


def test_a_library_without_notes_is_empty_rather_than_broken(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    assert SqliteNoteReadingRepository(connection).all() == ()
    assert SqliteNoteReadingRepository(connection).count() == 0


def test_a_version_six_database_gains_the_table(tmp_path: Path) -> None:
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
    legacy.execute("INSERT INTO schema_version (version) VALUES (6)")
    legacy.commit()
    legacy.close()

    connection = connect(path)
    assert connection.execute("SELECT version FROM schema_version").fetchone()[0] == SCHEMA_VERSION
    assert SqliteNoteReadingRepository(connection).all() == ()
    assert SqlitePhotoRepository(connection).all() == ()
