"""Every reading remembers the prompt version that made it.

The column is additive (schema 5): rows written before it keep NULL,
which says honestly that the prompt version was not recorded, not
that it was empty. See ADR-0051.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from kiseki.adapters.sqlite.store import (
    SCHEMA_VERSION,
    SqliteCaptionRepository,
    SqliteScreenshotReadingRepository,
    SqliteSingleCaptionRepository,
    SqliteSubjectRepository,
    SqliteThemeSetRepository,
    connect,
)
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.caption.themes import Theme, ThemeSet, ThemeSetKey
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.screen.reading import ScreenshotReading

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)
KEY = CaptionKey.of([PhotoId("sha256:aa")])


def test_the_schema_is_at_five(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    stored = connection.execute("SELECT version FROM schema_version").fetchone()
    assert stored[0] == SCHEMA_VERSION == 5


def test_a_caption_keeps_its_prompt_version(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteCaptionRepository(connection)
    repository.save(
        Caption(
            key=KEY,
            photo_ids=(PhotoId("sha256:aa"),),
            text="a bowl of ramen",
            model="vl",
            created_at=WHEN,
            prompt_version="stay-caption/3",
        )
    )
    kept = repository.get(KEY)
    assert kept is not None
    assert kept.prompt_version == "stay-caption/3"
    assert repository.all()[0].prompt_version == "stay-caption/3"


def test_a_single_caption_keeps_its_prompt_version(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteSingleCaptionRepository(connection)
    repository.save(
        SingleCaption(
            photo_id=PhotoId("sha256:bb"),
            text="a bowl of ramen",
            model="vl",
            created_at=WHEN,
            prompt_version="single-caption/1",
        )
    )
    kept = repository.get(PhotoId("sha256:bb"))
    assert kept is not None
    assert kept.prompt_version == "single-caption/1"


def test_a_subject_reading_keeps_its_prompt_version(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteSubjectRepository(connection)
    repository.save(
        SubjectExtraction(
            key=KEY,
            labels=("ramen",),
            model="lm",
            created_at=WHEN,
            prompt_version="subjects/2",
        )
    )
    kept = repository.get(KEY)
    assert kept is not None
    assert kept.prompt_version == "subjects/2"


def test_a_theme_set_keeps_its_prompt_version(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteThemeSetRepository(connection)
    key = ThemeSetKey.of(["ramen", "udon"])
    repository.save(
        ThemeSet(
            key=key,
            themes=(Theme(name="food", members=("ramen", "udon")),),
            model="lm",
            created_at=WHEN,
            prompt_version="themes/1",
        )
    )
    kept = repository.get(key)
    assert kept is not None
    assert kept.prompt_version == "themes/1"
    latest = repository.latest()
    assert latest is not None
    assert latest.prompt_version == "themes/1"


def test_a_screen_reading_keeps_its_prompt_version(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteScreenshotReadingRepository(connection)
    repository.save(
        ScreenshotReading(
            photo_id=PhotoId("sha256:cc"),
            category="map",
            labels=("route",),
            model="vl",
            created_at=WHEN,
            prompt_version="screen/4",
        )
    )
    kept = repository.get(PhotoId("sha256:cc"))
    assert kept is not None
    assert kept.prompt_version == "screen/4"


def test_a_version_four_database_reads_as_unrecorded(tmp_path: Path) -> None:
    """An older row keeps NULL: the version was not recorded, honestly."""
    path = tmp_path / "legacy.sqlite3"
    legacy = sqlite3.connect(path)
    legacy.executescript(
        "CREATE TABLE schema_version (version INTEGER NOT NULL);"
        " CREATE TABLE captions ("
        " key TEXT PRIMARY KEY, photo_ids TEXT NOT NULL, text TEXT NOT NULL,"
        " model TEXT NOT NULL, created_at TEXT NOT NULL, refused TEXT);"
    )
    legacy.execute("INSERT INTO schema_version (version) VALUES (4)")
    legacy.execute(
        "INSERT INTO captions (key, photo_ids, text, model, created_at, refused)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (KEY.value, '["sha256:aa"]', "a bowl of ramen", "vl", WHEN.isoformat(), None),
    )
    legacy.commit()
    legacy.close()

    connection = connect(path)
    stored = connection.execute("SELECT version FROM schema_version").fetchone()
    assert stored[0] == 5
    kept = SqliteCaptionRepository(connection).get(KEY)
    assert kept is not None
    assert kept.prompt_version is None
