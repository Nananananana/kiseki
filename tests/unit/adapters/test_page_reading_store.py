"""Page readings are stored beside everything else, and touch none of it."""

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import (
    SCHEMA_VERSION,
    SqliteNoteReadingRepository,
    SqlitePageReadingRepository,
    SqlitePhotoRepository,
    connect,
)
from kiseki.domain.web.reading import PageReading

WHEN = datetime(2026, 8, 30, 12, tzinfo=UTC)


def _reading(
    reference: str,
    category: str = "reading",
    labels: tuple[str, ...] = ("raft",),
    day: date = date(2026, 8, 30),
) -> PageReading:
    return PageReading(
        reference=reference,
        day=day,
        category=category,
        labels=labels,
        model="demo",
        created_at=WHEN,
    )


def test_the_schema_is_at_nine(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    stored = connection.execute("SELECT version FROM schema_version").fetchone()
    assert stored[0] == SCHEMA_VERSION


def test_a_reading_survives_the_round_trip(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqlitePageReadingRepository(connection)
    repository.save(_reading("page:9f7630c78bfc0a41"))
    held = repository.all()
    assert len(held) == 1
    assert held[0].reference == "page:9f7630c78bfc0a41"
    assert held[0].labels == ("raft",)


def test_a_page_read_again_on_the_same_day_replaces_rather_than_doubles(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqlitePageReadingRepository(connection)
    repository.save(_reading("page:aaaa", labels=("raft",)))
    repository.save(_reading("page:aaaa", labels=("paxos",)))
    held = repository.all()
    assert len(held) == 1
    assert held[0].labels == ("paxos",)


def test_a_page_returned_to_on_another_day_is_another_reading(tmp_path: Path) -> None:
    """The returning is the evidence (ADR-0076)."""
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqlitePageReadingRepository(connection)
    repository.save(_reading("page:aaaa", day=date(2026, 8, 30)))
    repository.save(_reading("page:aaaa", day=date(2026, 11, 2)))
    assert repository.count() == 2


def test_an_empty_table_is_what_a_library_without_pages_has(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    assert SqlitePageReadingRepository(connection).all() == ()
    assert SqlitePageReadingRepository(connection).count() == 0


def test_a_version_eight_database_gains_the_table(tmp_path: Path) -> None:
    """An explicit migration, and nothing else moves (ADR-0018)."""
    path = tmp_path / "legacy.sqlite3"
    legacy = sqlite3.connect(path)
    legacy.executescript(
        "CREATE TABLE schema_version (version INTEGER NOT NULL);"
        " CREATE TABLE photos ("
        " id TEXT PRIMARY KEY, captured_at TEXT NOT NULL, latitude REAL,"
        " longitude REAL, thumbnail_ref TEXT, content_kind TEXT,"
        " use_for_preference INTEGER);"
        " CREATE TABLE note_readings ("
        " reference TEXT NOT NULL, day TEXT NOT NULL, category TEXT NOT NULL,"
        " labels TEXT NOT NULL, model TEXT NOT NULL, created_at TEXT NOT NULL,"
        " refused TEXT, prompt_version TEXT, PRIMARY KEY (reference, day));"
    )
    legacy.execute("INSERT INTO schema_version (version) VALUES (8)")
    legacy.commit()
    legacy.close()

    connection = connect(path)
    assert connection.execute("SELECT version FROM schema_version").fetchone()[0] == SCHEMA_VERSION
    assert SqlitePageReadingRepository(connection).all() == ()
    assert SqliteNoteReadingRepository(connection).all() == ()
    assert SqlitePhotoRepository(connection).all() == ()


class TestWhatTheDomainRefuses:
    def test_a_category_that_carries_no_labels_arriving_with_labels(self) -> None:
        """Refused rather than trimmed. The producer promised not to
        send them, and quietly tidying it would hide a producer that
        had stopped keeping its promise."""
        with pytest.raises(ValueError):
            _reading("page:aaaa", category="health", labels=("a clinic",))

    def test_a_category_nobody_defined(self) -> None:
        with pytest.raises(ValueError):
            _reading("page:aaaa", category="fascinating")

    def test_a_reading_with_no_reference(self) -> None:
        with pytest.raises(ValueError):
            _reading("   ")

    def test_more_labels_than_a_page_may_carry(self) -> None:
        with pytest.raises(ValueError):
            _reading("page:aaaa", labels=tuple(f"label {n}" for n in range(9)))

    def test_a_refusal_may_name_a_category_nobody_defined(self) -> None:
        """A refusal is not a classification, so it is not held to the
        vocabulary of one."""
        reading = PageReading(
            reference="page:aaaa",
            day=date(2026, 8, 30),
            category="whatever the model said",
            labels=(),
            model="demo",
            created_at=WHEN,
            refused="the model did not answer with JSON",
        )
        assert reading.answered is False
