"""A note read across months is a trail, and the trail is the evidence."""

from datetime import UTC, date, datetime
from pathlib import Path

from kiseki.adapters.sqlite.store import SqliteNoteReadingRepository, connect
from kiseki.domain.note.reading import NoteReading

WHEN = datetime(2026, 8, 29, 12, tzinfo=UTC)


def _reading(
    reference: str,
    day: date,
    labels: tuple[str, ...] = ("raft",),
    category: str = "reading",
) -> NoteReading:
    return NoteReading(
        reference=reference,
        day=day,
        category=category,
        labels=labels,
        model="demo",
        created_at=WHEN,
    )


def test_one_note_across_months_is_a_trail(tmp_path: Path) -> None:
    """The difference between a thought had once and one lived with."""
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteNoteReadingRepository(connection)
    for day, labels in (
        (date(2026, 3, 1), ("raft",)),
        (date(2026, 5, 14), ("raft", "consensus")),
        (date(2026, 8, 29), ("raft", "consensus", "quorum")),
    ):
        repository.save(_reading("note:aaaa", day, labels))
    readings = repository.all()
    assert len(readings) == 3
    assert [reading.day.month for reading in readings] == [3, 5, 8]
    assert readings[-1].labels == ("raft", "consensus", "quorum")


def test_the_same_note_on_the_same_day_is_one_reading(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteNoteReadingRepository(connection)
    repository.save(_reading("note:aaaa", date(2026, 8, 29), ("raft",)))
    repository.save(_reading("note:aaaa", date(2026, 8, 29), ("paxos",)))
    readings = repository.all()
    assert len(readings) == 1
    assert readings[0].labels == ("paxos",)


def test_two_notes_on_one_day_are_two_readings(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteNoteReadingRepository(connection)
    repository.save(_reading("note:aaaa", date(2026, 8, 29)))
    repository.save(_reading("note:bbbb", date(2026, 8, 29)))
    assert len(repository.all()) == 2


def test_a_note_that_changed_category_keeps_both_readings(tmp_path: Path) -> None:
    """A project note that became a journal entry said both things."""
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteNoteReadingRepository(connection)
    repository.save(_reading("note:aaaa", date(2026, 1, 5), category="project"))
    repository.save(_reading("note:aaaa", date(2026, 8, 29), labels=(), category="journal"))
    assert [reading.category for reading in repository.all()] == ["project", "journal"]


def test_readings_come_back_in_the_order_they_were_written(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteNoteReadingRepository(connection)
    repository.save(_reading("note:bbbb", date(2026, 8, 29)))
    repository.save(_reading("note:aaaa", date(2026, 3, 1)))
    assert [reading.day.month for reading in repository.all()] == [3, 8]
