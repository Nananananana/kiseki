"""SQLite storage.

Timestamps are stored as ISO 8601 text including the offset. SQLite has no date
type, and text sorts correctly for a fixed offset while keeping the offset
itself, which the contract requires.

Profiles are stored whole, as JSON documents. A profile is read and replaced
as a unit and nothing yet queries inside one, so a document column carries it
with less machinery than a normalised shape would.
"""

import json
import sqlite3
from collections.abc import Sequence
from datetime import date as _date
from datetime import datetime
from pathlib import Path
from typing import Any

from kiseki.domain.activity.daily import DailyActivity
from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.caption.themes import Theme, ThemeSet, ThemeSetKey
from kiseki.domain.correction import Correction, CorrectionVerdict
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.note.reading import NoteReading
from kiseki.domain.outing.outing import Outing, OutingId
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.time_range import TimeRange
from kiseki.domain.web.reading import PageReading

SCHEMA_VERSION = 9

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS photos (
    id            TEXT PRIMARY KEY,
    captured_at   TEXT NOT NULL,
    latitude      REAL,
    longitude     REAL,
    thumbnail_ref TEXT,
    content_kind  TEXT,
    use_for_preference INTEGER
);
CREATE INDEX IF NOT EXISTS photos_captured_at ON photos (captured_at);

CREATE TABLE IF NOT EXISTS outings (
    id         TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS outings_started_at ON outings (started_at);

CREATE TABLE IF NOT EXISTS stops (
    outing_id  TEXT NOT NULL REFERENCES outings (id) ON DELETE CASCADE,
    sequence   INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    ended_at   TEXT NOT NULL,
    latitude   REAL NOT NULL,
    longitude  REAL NOT NULL,
    PRIMARY KEY (outing_id, sequence)
);

CREATE TABLE IF NOT EXISTS stop_photos (
    outing_id TEXT NOT NULL,
    sequence  INTEGER NOT NULL,
    position  INTEGER NOT NULL,
    photo_id  TEXT NOT NULL,
    PRIMARY KEY (outing_id, sequence, position),
    FOREIGN KEY (outing_id, sequence) REFERENCES stops (outing_id, sequence)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS anchors (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude         REAL NOT NULL,
    longitude        REAL NOT NULL,
    radius_m         REAL NOT NULL,
    started_at       TEXT NOT NULL,
    ended_at         TEXT NOT NULL,
    visit_days       INTEGER NOT NULL,
    night_days       INTEGER NOT NULL,
    weekday_days     INTEGER NOT NULL,
    daytime_days     INTEGER NOT NULL,
    photograph_count INTEGER NOT NULL,
    confidence       REAL NOT NULL,
    sample_size      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS profiles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at TEXT NOT NULL,
    document     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS captions (
    key        TEXT PRIMARY KEY,
    photo_ids  TEXT NOT NULL,
    text       TEXT NOT NULL,
    model      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    refused    TEXT,
    prompt_version TEXT
);

CREATE TABLE IF NOT EXISTS subjects (
    key        TEXT PRIMARY KEY,
    labels     TEXT NOT NULL,
    model      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    refused    TEXT,
    prompt_version TEXT
);

CREATE TABLE IF NOT EXISTS theme_sets (
    key        TEXT PRIMARY KEY,
    document   TEXT NOT NULL,
    model      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    prompt_version TEXT
);

CREATE TABLE IF NOT EXISTS screen_readings (
    photo_id   TEXT PRIMARY KEY,
    category   TEXT NOT NULL,
    labels     TEXT NOT NULL,
    model      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    refused    TEXT,
    prompt_version TEXT
);

CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT NOT NULL,
    verdict TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS note_readings (
    reference  TEXT NOT NULL,
    day        TEXT NOT NULL,
    category   TEXT NOT NULL,
    labels     TEXT NOT NULL,
    model      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    refused    TEXT,
    prompt_version TEXT,
    PRIMARY KEY (reference, day)
);

CREATE TABLE IF NOT EXISTS page_readings (
    reference  TEXT NOT NULL,
    day        TEXT NOT NULL,
    category   TEXT NOT NULL,
    labels     TEXT NOT NULL,
    model      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    refused    TEXT,
    prompt_version TEXT,
    PRIMARY KEY (reference, day)
);

CREATE TABLE IF NOT EXISTS daily_activity (
    day        TEXT PRIMARY KEY,
    steps      INTEGER NOT NULL,
    distance_m REAL,
    floors     INTEGER
);

CREATE TABLE IF NOT EXISTS single_captions (
    photo_id   TEXT PRIMARY KEY,
    text       TEXT NOT NULL,
    model      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    refused    TEXT,
    prompt_version TEXT
);
"""


def connect(path: Path) -> sqlite3.Connection:
    """Open the database, creating it and its directory if needed.

    Refuses a database written by a different schema version rather than
    guessing at a migration.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)

    stored = connection.execute("SELECT version FROM schema_version").fetchone()
    if stored is None:
        connection.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    else:
        version = stored[0]
        if version == 1:
            _migrate_v1_to_v2(connection)
            version = 2
        if version == 2:
            _migrate_v2_to_v3(connection)
            version = 3
        if version == 3:
            _migrate_v3_to_v4(connection)
            version = 4
        if version == 4:
            _migrate_v4_to_v5(connection)
            version = 5
        if version == 5:
            _migrate_v5_to_v6(connection)
            version = 6
        if version == 6:
            _migrate_v6_to_v7(connection)
            version = 7
        if version == 7:
            _migrate_v7_to_v8(connection)
            version = 8
        if version == 8:
            _migrate_v8_to_v9(connection)
            version = 9
        if version != SCHEMA_VERSION:
            connection.close()
            raise ValueError(f"database is at schema {version}, expected {SCHEMA_VERSION}")

    connection.commit()
    return connection


def _migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
    """The one change from 1 to 2: photos gained a thumbnail reference.

    Additive and explicit. Existing rows keep NULL, meaning the record
    predates the field; any version this code does not know is still
    refused rather than guessed at. See ADR-0018.
    """
    connection.execute("ALTER TABLE photos ADD COLUMN thumbnail_ref TEXT")
    connection.execute("UPDATE schema_version SET version = ?", (2,))


def _migrate_v2_to_v3(connection: sqlite3.Connection) -> None:
    """The one change from 2 to 3: photos gained a content kind.

    Additive and explicit, in the shape of ADR-0018. Existing rows
    keep NULL, meaning the record predates the field; by the rules of
    their time those were camera photographs. See ADR-0028.
    """
    connection.execute("ALTER TABLE photos ADD COLUMN content_kind TEXT")
    connection.execute("UPDATE schema_version SET version = ?", (3,))


def _migrate_v3_to_v4(connection: sqlite3.Connection) -> None:
    """The one change from 3 to 4: photos gained the preference consent.

    Additive and explicit (ADR-0018). Existing rows keep NULL, which
    counts as consent. See ADR-0032.
    """
    connection.execute("ALTER TABLE photos ADD COLUMN use_for_preference INTEGER")
    connection.execute("UPDATE schema_version SET version = ?", (4,))


def _migrate_v7_to_v8(connection: sqlite3.Connection) -> None:
    """The one change from 7 to 8: a note may be read more than once.

    Version 7 keyed a note reading by the note, which made a second
    reading a correction of the first. A note is not a state to be
    kept current; it is a thing the owner returned to, and the times
    they returned are the evidence (ADR-0076).

    SQLite cannot widen a primary key in place, so the table is
    rebuilt and every existing row carried over. Each of them is a
    first sighting, which is exactly what it was.
    """
    connection.executescript(
        "ALTER TABLE note_readings RENAME TO note_readings_v7;"
        " CREATE TABLE note_readings ("
        " reference TEXT NOT NULL, day TEXT NOT NULL, category TEXT NOT NULL,"
        " labels TEXT NOT NULL, model TEXT NOT NULL, created_at TEXT NOT NULL,"
        " refused TEXT, prompt_version TEXT,"
        " PRIMARY KEY (reference, day));"
        " INSERT INTO note_readings"
        " (reference, day, category, labels, model, created_at, refused, prompt_version)"
        " SELECT reference, day, category, labels, model, created_at, refused,"
        " prompt_version FROM note_readings_v7;"
        " DROP TABLE note_readings_v7;"
    )
    connection.execute("UPDATE schema_version SET version = ?", (8,))


def _migrate_v8_to_v9(connection: sqlite3.Connection) -> None:
    """The one change from 8 to 9: a table for page readings.

    A fourth kind of witness, in a table of its own. Photographs, days
    of movement and notes are untouched, and a library that never reads
    a page has an empty table -- which every derivation must survive
    (ADR-0063, ADR-0065).

    Keyed by reference and day from the start, because the lesson of
    the seventh migration is already learnt: a page is not a state to
    be kept current, it is something the owner returned to, and the
    times they returned are the evidence (ADR-0076).
    """
    connection.execute(
        "CREATE TABLE IF NOT EXISTS page_readings ("
        " reference TEXT NOT NULL, day TEXT NOT NULL,"
        " category TEXT NOT NULL, labels TEXT NOT NULL,"
        " model TEXT NOT NULL, created_at TEXT NOT NULL,"
        " refused TEXT, prompt_version TEXT,"
        " PRIMARY KEY (reference, day))"
    )
    connection.execute("UPDATE schema_version SET version = ?", (9,))


def _migrate_v6_to_v7(connection: sqlite3.Connection) -> None:
    """The one change from 6 to 7: a table for note readings.

    A third kind of witness, in a table of its own. Photographs and
    days of movement are untouched, and a library that never reads a
    note has an empty table -- which every derivation must survive
    (ADR-0063, ADR-0075).
    """
    connection.execute(
        "CREATE TABLE IF NOT EXISTS note_readings ("
        " reference TEXT NOT NULL, day TEXT NOT NULL,"
        " category TEXT NOT NULL, labels TEXT NOT NULL,"
        " model TEXT NOT NULL, created_at TEXT NOT NULL,"
        " refused TEXT, prompt_version TEXT,"
        " PRIMARY KEY (reference, day))"
    )
    connection.execute("UPDATE schema_version SET version = ?", (7,))


class SqliteNoteReadingRepository:
    """Note readings, keyed by the reference the producer made."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, reading: NoteReading) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO note_readings"
                " (reference, day, category, labels, model, created_at,"
                " refused, prompt_version)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    reading.reference,
                    reading.day.isoformat(),
                    reading.category,
                    json.dumps(list(reading.labels)),
                    reading.model,
                    reading.created_at.isoformat(),
                    reading.refused,
                    reading.prompt_version,
                ),
            )

    def save_all(self, readings: Sequence[NoteReading]) -> None:
        for reading in readings:
            self.save(reading)

    def all(self) -> tuple[NoteReading, ...]:
        rows = self._connection.execute(
            "SELECT reference, day, category, labels, model, created_at,"
            " refused, prompt_version FROM note_readings ORDER BY day, reference"
        )
        return tuple(
            NoteReading(
                reference=reference,
                day=_date.fromisoformat(day),
                category=category,
                labels=tuple(json.loads(labels)),
                model=model,
                created_at=datetime.fromisoformat(created_at),
                refused=refused,
                prompt_version=prompt_version,
            )
            for reference, day, category, labels, model, created_at, refused, prompt_version in rows
        )

    def count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) FROM note_readings").fetchone()
        total: int = row[0]
        return total


class SqlitePageReadingRepository:
    """Page readings, keyed by the reference the producer made."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, reading: PageReading) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO page_readings"
                " (reference, day, category, labels, model, created_at,"
                " refused, prompt_version)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    reading.reference,
                    reading.day.isoformat(),
                    reading.category,
                    json.dumps(list(reading.labels)),
                    reading.model,
                    reading.created_at.isoformat(),
                    reading.refused,
                    reading.prompt_version,
                ),
            )

    def save_all(self, readings: Sequence[PageReading]) -> None:
        for reading in readings:
            self.save(reading)

    def all(self) -> tuple[PageReading, ...]:
        rows = self._connection.execute(
            "SELECT reference, day, category, labels, model, created_at,"
            " refused, prompt_version FROM page_readings ORDER BY day, reference"
        )
        return tuple(
            PageReading(
                reference=reference,
                day=_date.fromisoformat(day),
                category=category,
                labels=tuple(json.loads(labels)),
                model=model,
                created_at=datetime.fromisoformat(created_at),
                refused=refused,
                prompt_version=prompt_version,
            )
            for reference, day, category, labels, model, created_at, refused, prompt_version in rows
        )

    def count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) FROM page_readings").fetchone()
        total: int = row[0]
        return total


def _migrate_v5_to_v6(connection: sqlite3.Connection) -> None:
    """The one change from 5 to 6: a table for daily activity.

    A new kind of witness arrives as its own table rather than as a
    column on somebody else''s. Photographs are untouched, and a library
    that never records a step is a library with an empty table -- which
    every derivation is required to survive (ADR-0063, ADR-0065).
    """
    connection.execute(
        "CREATE TABLE IF NOT EXISTS daily_activity ("
        " day TEXT PRIMARY KEY, steps INTEGER NOT NULL,"
        " distance_m REAL, floors INTEGER)"
    )
    connection.execute("UPDATE schema_version SET version = ?", (6,))


class SqliteDailyActivityRepository:
    """Days of movement, one row per calendar day."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_all(self, days: Sequence[DailyActivity]) -> None:
        """Store these days, replacing any already held for them."""
        with self._connection:
            self._connection.executemany(
                "INSERT OR REPLACE INTO daily_activity"
                " (day, steps, distance_m, floors) VALUES (?, ?, ?, ?)",
                [(day.day.isoformat(), day.steps, day.distance_m, day.floors) for day in days],
            )

    def all(self) -> tuple[DailyActivity, ...]:
        rows = self._connection.execute(
            "SELECT day, steps, distance_m, floors FROM daily_activity ORDER BY day"
        )
        return tuple(
            DailyActivity(
                day=_date.fromisoformat(day),
                steps=steps,
                distance_m=distance,
                floors=floors,
            )
            for day, steps, distance, floors in rows
        )

    def count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) FROM daily_activity").fetchone()
        total: int = row[0]
        return total


def _to_observation(row: tuple[Any, ...]) -> PhotoObservation:
    identifier, captured_at, latitude, longitude, thumbnail_ref, content_kind, preference = row
    place = GeoPoint(latitude, longitude) if latitude is not None else None
    return PhotoObservation(
        PhotoId(identifier),
        datetime.fromisoformat(captured_at),
        place,
        thumbnail_ref=thumbnail_ref,
        content_kind=content_kind,
        use_for_preference=None if preference is None else bool(preference),
    )


class SqlitePhotoRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_all(self, observations: Sequence[PhotoObservation]) -> int:
        rows = [
            (
                item.photo_id.value,
                item.captured_at.isoformat(),
                item.location.latitude if item.location else None,
                item.location.longitude if item.location else None,
                item.thumbnail_ref,
                item.content_kind,
                None if item.use_for_preference is None else int(item.use_for_preference),
            )
            for item in observations
        ]
        with self._connection:
            self._connection.executemany(
                "INSERT OR REPLACE INTO photos"
                " (id, captured_at, latitude, longitude, thumbnail_ref, content_kind,"
                " use_for_preference)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    def all(self) -> tuple[PhotoObservation, ...]:
        cursor = self._connection.execute(
            "SELECT id, captured_at, latitude, longitude, thumbnail_ref, content_kind,"
            " use_for_preference FROM photos ORDER BY captured_at"
        )
        return tuple(_to_observation(row) for row in cursor)

    def between(self, start: datetime, end: datetime) -> tuple[PhotoObservation, ...]:
        cursor = self._connection.execute(
            "SELECT id, captured_at, latitude, longitude, thumbnail_ref, content_kind,"
            " use_for_preference FROM photos"
            " WHERE captured_at >= ? AND captured_at <= ? ORDER BY captured_at",
            (start.isoformat(), end.isoformat()),
        )
        return tuple(_to_observation(row) for row in cursor)

    def count(self) -> int:
        total: int = self._connection.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
        return total


class SqliteOutingRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def replace_all(self, outings: Sequence[Outing]) -> int:
        with self._connection:
            self._connection.execute("DELETE FROM outings")
            for outing in outings:
                self._connection.execute(
                    "INSERT INTO outings (id, started_at, ended_at) VALUES (?, ?, ?)",
                    (
                        outing.id.value,
                        outing.time_range.start.isoformat(),
                        outing.time_range.end.isoformat(),
                    ),
                )
                for sequence, stop in enumerate(outing.stops):
                    self._connection.execute(
                        "INSERT INTO stops (outing_id, sequence, started_at, ended_at,"
                        " latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            outing.id.value,
                            sequence,
                            stop.time_range.start.isoformat(),
                            stop.time_range.end.isoformat(),
                            stop.centroid.latitude,
                            stop.centroid.longitude,
                        ),
                    )
                    self._connection.executemany(
                        "INSERT INTO stop_photos (outing_id, sequence, position, photo_id)"
                        " VALUES (?, ?, ?, ?)",
                        [
                            (outing.id.value, sequence, position, identifier.value)
                            for position, identifier in enumerate(stop.photo_ids)
                        ],
                    )
        return len(outings)

    def all(self) -> tuple[Outing, ...]:
        outings = []
        rows = self._connection.execute("SELECT id FROM outings ORDER BY started_at")
        for (outing_id,) in rows.fetchall():
            outings.append(Outing(OutingId(outing_id), self._stops_of(outing_id)))
        return tuple(outings)

    def _stops_of(self, outing_id: str) -> tuple[Stop, ...]:
        rows = self._connection.execute(
            "SELECT sequence, started_at, ended_at, latitude, longitude FROM stops"
            " WHERE outing_id = ? ORDER BY sequence",
            (outing_id,),
        ).fetchall()

        stops = []
        for sequence, started, ended, latitude, longitude in rows:
            photo_ids = tuple(
                PhotoId(value)
                for (value,) in self._connection.execute(
                    "SELECT photo_id FROM stop_photos WHERE outing_id = ? AND sequence = ?"
                    " ORDER BY position",
                    (outing_id, sequence),
                ).fetchall()
            )
            stops.append(
                Stop(
                    photo_ids,
                    TimeRange(datetime.fromisoformat(started), datetime.fromisoformat(ended)),
                    GeoPoint(latitude, longitude),
                )
            )
        return tuple(stops)


class SqliteAnchorRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def replace_all(self, anchors: Sequence[Anchor]) -> int:
        with self._connection:
            self._connection.execute("DELETE FROM anchors")
            self._connection.executemany(
                "INSERT INTO anchors (latitude, longitude, radius_m, started_at, ended_at,"
                " visit_days, night_days, weekday_days, daytime_days, photograph_count,"
                " confidence, sample_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        anchor.area.center.latitude,
                        anchor.area.center.longitude,
                        anchor.area.radius.meters,
                        anchor.period.start.isoformat(),
                        anchor.period.end.isoformat(),
                        anchor.visit_days,
                        anchor.night_days,
                        anchor.weekday_days,
                        anchor.daytime_days,
                        anchor.photograph_count,
                        anchor.confidence.value,
                        anchor.confidence.sample_size,
                    )
                    for anchor in anchors
                ],
            )
        return len(anchors)

    def all(self) -> tuple[Anchor, ...]:
        cursor = self._connection.execute(
            "SELECT latitude, longitude, radius_m, started_at, ended_at, visit_days,"
            " night_days, weekday_days, daytime_days, photograph_count, confidence,"
            " sample_size FROM anchors ORDER BY visit_days DESC"
        )
        return tuple(
            Anchor(
                area=GeoArea(GeoPoint(row[0], row[1]), Distance(row[2])),
                period=TimeRange(datetime.fromisoformat(row[3]), datetime.fromisoformat(row[4])),
                visit_days=row[5],
                night_days=row[6],
                weekday_days=row[7],
                daytime_days=row[8],
                photograph_count=row[9],
                confidence=Confidence(row[10], row[11]),
            )
            for row in cursor
        )


def _profile_document(profile: Profile) -> dict[str, Any]:
    return {
        "generated_at": profile.generated_at.isoformat(),
        "interests": [
            {
                "topic": interest.topic,
                "score": interest.score,
                "confidence": interest.confidence,
                "first_seen": interest.first_seen.isoformat(),
                "last_seen": interest.last_seen.isoformat(),
                "evidence": [
                    {
                        "kind": evidence.kind.value,
                        "reference": evidence.reference,
                        "observed_at": evidence.observed_at.isoformat(),
                    }
                    for evidence in interest.evidence
                ],
            }
            for interest in profile.interests
        ],
    }


def _profile_from(document: str) -> Profile:
    data = json.loads(document)
    interests = tuple(
        Interest(
            topic=item["topic"],
            score=item["score"],
            confidence=item["confidence"],
            evidence=tuple(
                InterestEvidence(
                    kind=EvidenceKind(entry["kind"]),
                    reference=entry["reference"],
                    observed_at=datetime.fromisoformat(entry["observed_at"]),
                )
                for entry in item["evidence"]
            ),
            first_seen=datetime.fromisoformat(item["first_seen"]),
            last_seen=datetime.fromisoformat(item["last_seen"]),
        )
        for item in data["interests"]
    )
    return Profile(
        generated_at=datetime.fromisoformat(data["generated_at"]),
        interests=interests,
    )


class SqliteProfileRepository:
    """Profiles accumulate like photographs: every reading is kept.

    The history is the raw material a trend will be computed from, so
    nothing is replaced. Each profile is one JSON document; the table
    is additive to schema version 1, so an existing database gains it
    on connect without a migration.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, profile: Profile) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT INTO profiles (generated_at, document) VALUES (?, ?)",
                (profile.generated_at.isoformat(), json.dumps(_profile_document(profile))),
            )

    def latest(self) -> Profile | None:
        row = self._connection.execute(
            "SELECT document FROM profiles ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return _profile_from(row[0])

    def history(self) -> tuple[Profile, ...]:
        cursor = self._connection.execute("SELECT document FROM profiles ORDER BY id")
        return tuple(_profile_from(row[0]) for row in cursor)


PROMPT_VERSION_TABLES = (
    "captions",
    "subjects",
    "theme_sets",
    "screen_readings",
    "single_captions",
)


def _has_column(connection: sqlite3.Connection, table: str, column: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def _migrate_v4_to_v5(connection: sqlite3.Connection) -> None:
    """The one change from 4 to 5: every reading names its prompt version.

    Additive and explicit (ADR-0018). Existing rows keep NULL, which
    says the version was not recorded rather than that it was empty.
    A table created fresh by this version already has the column, so
    the migration asks before it adds. See ADR-0051.
    """
    for table in PROMPT_VERSION_TABLES:
        if not _has_column(connection, table, "prompt_version"):
            connection.execute(f"ALTER TABLE {table} ADD COLUMN prompt_version TEXT")
    connection.execute("UPDATE schema_version SET version = ?", (5,))


def _outdated_clause(table: str) -> str:
    """Answered readings whose prompt version is older, or unrecorded.

    A refusal is left alone: it is governed by ADR-0015, not by the
    prompt version. theme_sets has no refusal column, so it has no
    refusals to leave alone.
    """
    if table not in PROMPT_VERSION_TABLES:
        raise ValueError(f"{table!r} does not carry a prompt version")
    refusals = "" if table == "theme_sets" else " AND refused IS NULL"
    return f"(prompt_version IS NULL OR prompt_version <> ?){refusals}"


def count_outdated(connection: sqlite3.Connection, table: str, current: str) -> int:
    """How many readings an older prompt version left behind."""
    clause = _outdated_clause(table)
    row = connection.execute(f"SELECT COUNT(*) FROM {table} WHERE {clause}", (current,)).fetchone()
    total: int = row[0]
    return total


def clear_outdated(connection: sqlite3.Connection, table: str, current: str) -> int:
    """Remove those readings, so a resumable run makes them again.

    Nothing is rewritten in place and nothing is regenerated here:
    the rows go, and `kiseki caption`, `kiseki subjects` and their
    kin fill the gap on their next run. See ADR-0051.
    """
    clause = _outdated_clause(table)
    removed = count_outdated(connection, table, current)
    with connection:
        connection.execute(f"DELETE FROM {table} WHERE {clause}", (current,))
    return removed


REFUSAL_TABLES = ("captions", "subjects", "screen_readings", "single_captions")

RECOVERABLE_REFUSAL = "no thumbnail%"
"""A refusal the environment caused, not the model: the image the
reader needed was not on disk. See ADR-0052."""


def _recoverable_clause(table: str) -> str:
    if table not in REFUSAL_TABLES:
        raise ValueError(f"{table!r} does not record refusals")
    return "refused LIKE ?"


def count_recoverable(connection: sqlite3.Connection, table: str) -> int:
    """How many refusals the environment caused rather than the model."""
    clause = _recoverable_clause(table)
    row = connection.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {clause}", (RECOVERABLE_REFUSAL,)
    ).fetchone()
    total: int = row[0]
    return total


def clear_recoverable(connection: sqlite3.Connection, table: str) -> int:
    """Take those refusals back, so a resumable run may try again.

    The model's own refusals stay exactly where they are (ADR-0015).
    Nothing is regenerated here: the rows go, and the next run of the
    stage asks again -- and records the same refusal if the image is
    still missing. See ADR-0052.
    """
    clause = _recoverable_clause(table)
    removed = count_recoverable(connection, table)
    with connection:
        connection.execute(f"DELETE FROM {table} WHERE {clause}", (RECOVERABLE_REFUSAL,))
    return removed


def _to_caption(row: tuple[Any, ...]) -> Caption:
    key, photo_ids, text, model, created_at, refused, prompt_version = row
    return Caption(
        key=CaptionKey(key),
        photo_ids=tuple(PhotoId(value) for value in json.loads(photo_ids)),
        text=text,
        model=model,
        created_at=datetime.fromisoformat(created_at),
        refused=refused,
        prompt_version=prompt_version,
    )


class SqliteCaptionRepository:
    """Captions accumulate, keyed by the photographs they describe.

    Never replaced wholesale: a caption costs model time measured in
    hours, and its key already changes exactly when the stay it
    describes is a different stay. The table is additive to schema
    version 2, so an existing database gains it on connect. See
    ADR-0019.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, caption: Caption) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO captions"
                " (key, photo_ids, text, model, created_at, refused, prompt_version)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    caption.key.value,
                    json.dumps([identifier.value for identifier in caption.photo_ids]),
                    caption.text,
                    caption.model,
                    caption.created_at.isoformat(),
                    caption.refused,
                    caption.prompt_version,
                ),
            )

    def get(self, key: CaptionKey) -> Caption | None:
        row = self._connection.execute(
            "SELECT key, photo_ids, text, model, created_at, refused, prompt_version"
            " FROM captions WHERE key = ?",
            (key.value,),
        ).fetchone()
        if row is None:
            return None
        return _to_caption(row)

    def all(self) -> tuple[Caption, ...]:
        cursor = self._connection.execute(
            "SELECT key, photo_ids, text, model, created_at, refused, prompt_version"
            " FROM captions ORDER BY rowid"
        )
        return tuple(_to_caption(row) for row in cursor)


def _to_subjects(row: tuple[Any, ...]) -> SubjectExtraction:
    key, labels, model, created_at, refused, prompt_version = row
    return SubjectExtraction(
        key=CaptionKey(key),
        labels=tuple(json.loads(labels)),
        model=model,
        created_at=datetime.fromisoformat(created_at),
        refused=refused,
        prompt_version=prompt_version,
    )


class SqliteSubjectRepository:
    """Subject readings accumulate, keyed by the caption they read.

    The table is additive to schema version 2, so an existing database
    gains it on connect. See ADR-0020.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, reading: SubjectExtraction) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO subjects"
                " (key, labels, model, created_at, refused, prompt_version)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    reading.key.value,
                    json.dumps(list(reading.labels)),
                    reading.model,
                    reading.created_at.isoformat(),
                    reading.refused,
                    reading.prompt_version,
                ),
            )

    def get(self, key: CaptionKey) -> SubjectExtraction | None:
        row = self._connection.execute(
            "SELECT key, labels, model, created_at, refused, prompt_version"
            " FROM subjects WHERE key = ?",
            (key.value,),
        ).fetchone()
        if row is None:
            return None
        return _to_subjects(row)

    def all(self) -> tuple[SubjectExtraction, ...]:
        cursor = self._connection.execute(
            "SELECT key, labels, model, created_at, refused, prompt_version"
            " FROM subjects ORDER BY rowid"
        )
        return tuple(_to_subjects(row) for row in cursor)


def _to_theme_set(row: tuple[Any, ...]) -> ThemeSet:
    key, document, model, created_at, prompt_version = row
    data = json.loads(document)
    themes = tuple(
        Theme(name=item["name"], members=tuple(item["members"])) for item in data["themes"]
    )
    return ThemeSet(
        key=ThemeSetKey(key),
        themes=themes,
        model=model,
        created_at=datetime.fromisoformat(created_at),
        prompt_version=prompt_version,
    )


class SqliteThemeSetRepository:
    """Theme sets accumulate, keyed by the label universe they read.

    The table is additive to schema version 2, so an existing database
    gains it on connect. See ADR-0023.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, theme_set: ThemeSet) -> None:
        document = json.dumps(
            {
                "themes": [
                    {"name": theme.name, "members": list(theme.members)}
                    for theme in theme_set.themes
                ]
            }
        )
        with self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO theme_sets"
                " (key, document, model, created_at, prompt_version)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    theme_set.key.value,
                    document,
                    theme_set.model,
                    theme_set.created_at.isoformat(),
                    theme_set.prompt_version,
                ),
            )

    def get(self, key: ThemeSetKey) -> ThemeSet | None:
        row = self._connection.execute(
            "SELECT key, document, model, created_at, prompt_version FROM theme_sets WHERE key = ?",
            (key.value,),
        ).fetchone()
        if row is None:
            return None
        return _to_theme_set(row)

    def latest(self) -> ThemeSet | None:
        row = self._connection.execute(
            "SELECT key, document, model, created_at, prompt_version"
            " FROM theme_sets ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return _to_theme_set(row)


def _to_screen_reading(row: tuple[Any, ...]) -> "ScreenshotReading":
    photo_id, category, labels, model, created_at, refused, prompt_version = row
    return ScreenshotReading(
        photo_id=PhotoId(photo_id),
        category=category,
        labels=tuple(json.loads(labels)),
        model=model,
        created_at=datetime.fromisoformat(created_at),
        refused=refused,
        prompt_version=prompt_version,
    )


class SqliteScreenshotReadingRepository:
    """Screen readings accumulate, keyed by the photograph they read.

    The table is additive to schema version 3, so an existing database
    gains it on connect. See ADR-0030.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, reading: ScreenshotReading) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO screen_readings"
                " (photo_id, category, labels, model, created_at, refused, prompt_version)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    reading.photo_id.value,
                    reading.category,
                    json.dumps(list(reading.labels)),
                    reading.model,
                    reading.created_at.isoformat(),
                    reading.refused,
                    reading.prompt_version,
                ),
            )

    def get(self, photo_id: PhotoId) -> ScreenshotReading | None:
        row = self._connection.execute(
            "SELECT photo_id, category, labels, model, created_at, refused, prompt_version"
            " FROM screen_readings WHERE photo_id = ?",
            (photo_id.value,),
        ).fetchone()
        if row is None:
            return None
        return _to_screen_reading(row)

    def all(self) -> tuple[ScreenshotReading, ...]:
        cursor = self._connection.execute(
            "SELECT photo_id, category, labels, model, created_at, refused, prompt_version"
            " FROM screen_readings ORDER BY rowid"
        )
        return tuple(_to_screen_reading(row) for row in cursor)


def _to_single_caption(row: tuple[Any, ...]) -> SingleCaption:
    photo_id, text, model, created_at, refused, prompt_version = row
    return SingleCaption(
        photo_id=PhotoId(photo_id),
        text=text,
        model=model,
        created_at=datetime.fromisoformat(created_at),
        refused=refused,
        prompt_version=prompt_version,
    )


class SqliteSingleCaptionRepository:
    """Single captions accumulate, keyed by the photograph they describe.

    The table is additive to schema version 4, so an existing database
    gains it on connect. See ADR-0033.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, caption: SingleCaption) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO single_captions"
                " (photo_id, text, model, created_at, refused, prompt_version)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    caption.photo_id.value,
                    caption.text,
                    caption.model,
                    caption.created_at.isoformat(),
                    caption.refused,
                    caption.prompt_version,
                ),
            )

    def get(self, photo_id: PhotoId) -> SingleCaption | None:
        row = self._connection.execute(
            "SELECT photo_id, text, model, created_at, refused, prompt_version"
            " FROM single_captions WHERE photo_id = ?",
            (photo_id.value,),
        ).fetchone()
        if row is None:
            return None
        return _to_single_caption(row)

    def all(self) -> tuple[SingleCaption, ...]:
        cursor = self._connection.execute(
            "SELECT photo_id, text, model, created_at, refused, prompt_version"
            " FROM single_captions ORDER BY rowid"
        )
        return tuple(_to_single_caption(row) for row in cursor)


class SqliteCorrectionRepository:
    """Corrections accumulate and are never rewritten.

    The table is additive to schema version 4, so an existing
    database gains it on connect. Append-only by contract: there is
    no UPDATE and no DELETE here. See ADR-0044.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, correction: Correction) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT INTO corrections (reference, verdict, note, created_at)"
                " VALUES (?, ?, ?, ?)",
                (
                    correction.reference,
                    correction.verdict.value,
                    correction.note,
                    correction.created_at.isoformat(),
                ),
            )

    def all(self) -> tuple[Correction, ...]:
        cursor = self._connection.execute(
            "SELECT reference, verdict, note, created_at FROM corrections ORDER BY rowid"
        )
        return tuple(
            Correction(
                reference=reference,
                verdict=CorrectionVerdict(verdict),
                note=note,
                created_at=datetime.fromisoformat(created_at),
            )
            for reference, verdict, note, created_at in cursor
        )
