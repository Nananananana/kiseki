"""Forgetting a photograph, and everything that was said about it.

Every promise this library makes about privacy assumes the owner can
take something back. Until now they could not: deleting a photograph
left its caption, its subjects, its screen reading, its indexed text
and its embedding exactly where they were, and the profile went on
speaking from evidence that no longer existed.

This is the whole path, named in one place so it cannot drift:

    photographs      the observation itself
    single_captions  what a model said about that one photograph
    screen_readings   the category and labels, if it was a screenshot
    captions         any stay caption whose photographs include it
    subjects         the labels read from those captions
    search_documents the indexed text of all of the above
    search_embeddings the vectors of those documents

Journeys are not in the list because they are derived: a rebuild
without the photograph produces stops and outings without it
(ADR-0013). Corrections are not in the list either -- "that reading
was wrong" stays true after the reading is gone, and the doctor
reports a correction that no longer reaches anything.

Nothing here guesses. A plan is counted first and shown to the owner,
and only then, on a separate word, is anything removed. See ADR-0061.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

STAY_PREFIX = "stay:"
SINGLE_PREFIX = "single:"
SCREEN_PREFIX = "screen:"


@dataclass(frozen=True)
class ForgetPlan:
    """What disappears, counted before anything does."""

    photo_ids: tuple[str, ...]
    caption_keys: tuple[str, ...]
    single_captions: int
    screen_readings: int
    subjects: int
    documents: int
    embeddings: int

    @property
    def is_empty(self) -> bool:
        return not self.photo_ids

    @property
    def total(self) -> int:
        return (
            len(self.photo_ids)
            + len(self.caption_keys)
            + self.single_captions
            + self.screen_readings
            + self.subjects
            + self.documents
            + self.embeddings
        )


def _known_photographs(connection: sqlite3.Connection, wanted: Sequence[str]) -> tuple[str, ...]:
    found: list[str] = []
    for identifier in wanted:
        row = connection.execute("SELECT id FROM photos WHERE id = ?", (identifier,)).fetchone()
        if row is not None:
            found.append(row[0])
    return tuple(found)


def _captions_touching(connection: sqlite3.Connection, photo_ids: Sequence[str]) -> tuple[str, ...]:
    """Stay captions whose photographs include any of these.

    The photographs of a caption are stored as a JSON list, so the
    membership is decided in Python rather than in SQL: a LIKE against
    a JSON string would match an identifier that merely shares a prefix.
    """
    wanted = set(photo_ids)
    keys: list[str] = []
    for key, raw in connection.execute("SELECT key, photo_ids FROM captions"):
        if wanted & set(json.loads(raw)):
            keys.append(key)
    return tuple(keys)


def _count(connection: sqlite3.Connection, sql: str, values: Sequence[str]) -> int:
    """Count, treating a table that was never created as empty.

    A library that has never been indexed has no search tables, and
    nothing in them to forget. Asking is still correct; failing would
    make deletion depend on whether search had been set up.
    """
    if not values:
        return 0
    marks = ",".join("?" for _ in values)
    try:
        row = connection.execute(sql.format(marks=marks), tuple(values)).fetchone()
    except sqlite3.OperationalError:
        return 0
    total: int = row[0]
    return total


def _document_keys(photo_ids: Sequence[str], caption_keys: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        [f"{SINGLE_PREFIX}{identifier}" for identifier in photo_ids]
        + [f"{SCREEN_PREFIX}{identifier}" for identifier in photo_ids]
        + [f"{STAY_PREFIX}{key}" for key in caption_keys]
    )


def plan_forget(connection: sqlite3.Connection, photo_ids: Sequence[str]) -> ForgetPlan:
    """Count everything that would go, without touching any of it."""
    known = _known_photographs(connection, photo_ids)
    if not known:
        return ForgetPlan((), (), 0, 0, 0, 0, 0)
    captions = _captions_touching(connection, known)
    documents = _document_keys(known, captions)
    return ForgetPlan(
        photo_ids=known,
        caption_keys=captions,
        single_captions=_count(
            connection,
            "SELECT COUNT(*) FROM single_captions WHERE photo_id IN ({marks})",
            known,
        ),
        screen_readings=_count(
            connection,
            "SELECT COUNT(*) FROM screen_readings WHERE photo_id IN ({marks})",
            known,
        ),
        subjects=_count(
            connection, "SELECT COUNT(*) FROM subjects WHERE key IN ({marks})", captions
        ),
        documents=_count(
            connection,
            "SELECT COUNT(*) FROM search_documents WHERE doc_key IN ({marks})",
            documents,
        ),
        embeddings=_count(
            connection,
            "SELECT COUNT(*) FROM search_embeddings WHERE doc_key IN ({marks})",
            documents,
        ),
    )


def _delete(connection: sqlite3.Connection, sql: str, values: Sequence[str]) -> None:
    if not values:
        return
    marks = ",".join("?" for _ in values)
    try:
        connection.execute(sql.format(marks=marks), tuple(values))
    except sqlite3.OperationalError:
        return


def forget(connection: sqlite3.Connection, plan: ForgetPlan) -> ForgetPlan:
    """Remove exactly what the plan counted, in one transaction."""
    if plan.is_empty:
        return plan
    documents = _document_keys(plan.photo_ids, plan.caption_keys)
    with connection:
        _delete(
            connection,
            "DELETE FROM search_embeddings WHERE doc_key IN ({marks})",
            documents,
        )
        _delete(
            connection,
            "DELETE FROM search_documents WHERE doc_key IN ({marks})",
            documents,
        )
        _delete(connection, "DELETE FROM subjects WHERE key IN ({marks})", plan.caption_keys)
        _delete(connection, "DELETE FROM captions WHERE key IN ({marks})", plan.caption_keys)
        _delete(
            connection,
            "DELETE FROM screen_readings WHERE photo_id IN ({marks})",
            plan.photo_ids,
        )
        _delete(
            connection,
            "DELETE FROM single_captions WHERE photo_id IN ({marks})",
            plan.photo_ids,
        )
        _delete(connection, "DELETE FROM stop_photos WHERE photo_id IN ({marks})", plan.photo_ids)
        _delete(connection, "DELETE FROM photos WHERE id IN ({marks})", plan.photo_ids)
    return plan
