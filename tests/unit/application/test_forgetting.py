"""Forgetting leaves nothing behind that speaks for what was forgotten."""

import json
from datetime import UTC, datetime
from pathlib import Path

from kiseki.adapters.sqlite.search import SqliteSearchIndex
from kiseki.adapters.sqlite.store import (
    SqliteCaptionRepository,
    SqlitePhotoRepository,
    SqliteScreenshotReadingRepository,
    SqliteSingleCaptionRepository,
    SqliteSubjectRepository,
    connect,
)
from kiseki.application.forgetting import forget, plan_forget
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.ports.search import SearchDocument

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)
DOOMED = PhotoId("sha256:doomed")
SPARED = PhotoId("sha256:spared")


def _seeded(tmp_path: Path):
    connection = connect(tmp_path / "kiseki.sqlite3")
    SqlitePhotoRepository(connection).save_all(
        [PhotoObservation(DOOMED, WHEN), PhotoObservation(SPARED, WHEN)]
    )
    key = CaptionKey.of([DOOMED, SPARED])
    SqliteCaptionRepository(connection).save(
        Caption(
            key=key,
            photo_ids=(DOOMED, SPARED),
            text="a bowl of ramen",
            model="vl",
            created_at=WHEN,
        )
    )
    SqliteSubjectRepository(connection).save(
        SubjectExtraction(key=key, labels=("ramen",), model="lm", created_at=WHEN)
    )
    SqliteSingleCaptionRepository(connection).save(
        SingleCaption(photo_id=DOOMED, text="a doorway", model="vl", created_at=WHEN)
    )
    SqliteScreenshotReadingRepository(connection).save(
        ScreenshotReading(
            photo_id=DOOMED,
            category="map",
            labels=("route",),
            model="vl",
            created_at=WHEN,
        )
    )
    index = SqliteSearchIndex(connection)
    for doc_key, text in (
        (f"stay:{key.value}", "a bowl of ramen"),
        (f"single:{DOOMED.value}", "a doorway"),
        (f"screen:{DOOMED.value}", "route"),
        (f"single:{SPARED.value}", "a quiet street"),
    ):
        index.put_document(SearchDocument(doc_key, "stay", text, WHEN))
        index.put_embedding(doc_key, "m", (1.0, 0.0))
    return connection, key


def test_the_plan_counts_everything_before_anything_goes(tmp_path: Path) -> None:
    connection, _key = _seeded(tmp_path)
    plan = plan_forget(connection, [DOOMED.value])
    assert plan.photo_ids == (DOOMED.value,)
    assert len(plan.caption_keys) == 1
    assert plan.single_captions == 1
    assert plan.screen_readings == 1
    assert plan.subjects == 1
    assert plan.documents == 3
    assert plan.embeddings == 3
    assert SqlitePhotoRepository(connection).all()


def test_a_photograph_nobody_has_is_an_empty_plan(tmp_path: Path) -> None:
    connection, _key = _seeded(tmp_path)
    plan = plan_forget(connection, ["sha256:never-existed"])
    assert plan.is_empty
    assert plan.total == 0


def test_forgetting_leaves_no_reading_behind(tmp_path: Path) -> None:
    connection, key = _seeded(tmp_path)
    forget(connection, plan_forget(connection, [DOOMED.value]))
    photos = SqlitePhotoRepository(connection).all()
    assert [photo.photo_id for photo in photos] == [SPARED]
    assert SqliteCaptionRepository(connection).get(key) is None
    assert SqliteSubjectRepository(connection).get(key) is None
    assert SqliteSingleCaptionRepository(connection).get(DOOMED) is None
    assert SqliteScreenshotReadingRepository(connection).get(DOOMED) is None


def test_forgetting_leaves_nothing_in_the_index(tmp_path: Path) -> None:
    connection, key = _seeded(tmp_path)
    forget(connection, plan_forget(connection, [DOOMED.value]))
    index = SqliteSearchIndex(connection)
    assert not index.has_document(f"single:{DOOMED.value}")
    assert not index.has_document(f"screen:{DOOMED.value}")
    assert not index.has_document(f"stay:{key.value}")
    assert index.has_document(f"single:{SPARED.value}")
    assert index.embedding_count("m") == 1


def test_what_was_not_asked_for_stays(tmp_path: Path) -> None:
    connection, _key = _seeded(tmp_path)
    forget(connection, plan_forget(connection, [DOOMED.value]))
    row = connection.execute("SELECT COUNT(*) FROM photos WHERE id = ?", (SPARED.value,)).fetchone()
    assert row[0] == 1


def test_an_identifier_that_merely_shares_a_prefix_is_not_touched(
    tmp_path: Path,
) -> None:
    """A JSON list is not a string to be matched with LIKE."""
    connection = connect(tmp_path / "kiseki.sqlite3")
    short = PhotoId("sha256:aa")
    longer = PhotoId("sha256:aabb")
    SqlitePhotoRepository(connection).save_all(
        [PhotoObservation(short, WHEN), PhotoObservation(longer, WHEN)]
    )
    key = CaptionKey.of([longer])
    SqliteCaptionRepository(connection).save(
        Caption(
            key=key,
            photo_ids=(longer,),
            text="a bowl of ramen",
            model="vl",
            created_at=WHEN,
        )
    )
    plan = plan_forget(connection, [short.value])
    assert plan.caption_keys == ()
    raw = connection.execute("SELECT photo_ids FROM captions").fetchone()[0]
    assert json.loads(raw) == [longer.value]
