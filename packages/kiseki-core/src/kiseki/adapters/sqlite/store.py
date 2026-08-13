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
from datetime import datetime
from pathlib import Path
from typing import Any

from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.outing.outing import Outing, OutingId
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.time_range import TimeRange

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS photos (
    id            TEXT PRIMARY KEY,
    captured_at   TEXT NOT NULL,
    latitude      REAL,
    longitude     REAL,
    thumbnail_ref TEXT
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
    refused    TEXT
);

CREATE TABLE IF NOT EXISTS subjects (
    key        TEXT PRIMARY KEY,
    labels     TEXT NOT NULL,
    model      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    refused    TEXT
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
    elif stored[0] == 1:
        _migrate_v1_to_v2(connection)
    elif stored[0] != SCHEMA_VERSION:
        connection.close()
        raise ValueError(f"database is at schema {stored[0]}, expected {SCHEMA_VERSION}")

    connection.commit()
    return connection


def _migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
    """The one change from 1 to 2: photos gained a thumbnail reference.

    Additive and explicit. Existing rows keep NULL, meaning the record
    predates the field; any version this code does not know is still
    refused rather than guessed at. See ADR-0018.
    """
    connection.execute("ALTER TABLE photos ADD COLUMN thumbnail_ref TEXT")
    connection.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))


def _to_observation(row: tuple[Any, ...]) -> PhotoObservation:
    identifier, captured_at, latitude, longitude, thumbnail_ref = row
    place = GeoPoint(latitude, longitude) if latitude is not None else None
    return PhotoObservation(
        PhotoId(identifier),
        datetime.fromisoformat(captured_at),
        place,
        thumbnail_ref=thumbnail_ref,
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
            )
            for item in observations
        ]
        with self._connection:
            self._connection.executemany(
                "INSERT OR REPLACE INTO photos"
                " (id, captured_at, latitude, longitude, thumbnail_ref)"
                " VALUES (?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    def all(self) -> tuple[PhotoObservation, ...]:
        cursor = self._connection.execute(
            "SELECT id, captured_at, latitude, longitude, thumbnail_ref FROM photos"
            " ORDER BY captured_at"
        )
        return tuple(_to_observation(row) for row in cursor)

    def between(self, start: datetime, end: datetime) -> tuple[PhotoObservation, ...]:
        cursor = self._connection.execute(
            "SELECT id, captured_at, latitude, longitude, thumbnail_ref FROM photos"
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


def _to_caption(row: tuple[Any, ...]) -> Caption:
    key, photo_ids, text, model, created_at, refused = row
    return Caption(
        key=CaptionKey(key),
        photo_ids=tuple(PhotoId(value) for value in json.loads(photo_ids)),
        text=text,
        model=model,
        created_at=datetime.fromisoformat(created_at),
        refused=refused,
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
                " (key, photo_ids, text, model, created_at, refused)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    caption.key.value,
                    json.dumps([identifier.value for identifier in caption.photo_ids]),
                    caption.text,
                    caption.model,
                    caption.created_at.isoformat(),
                    caption.refused,
                ),
            )

    def get(self, key: CaptionKey) -> Caption | None:
        row = self._connection.execute(
            "SELECT key, photo_ids, text, model, created_at, refused FROM captions WHERE key = ?",
            (key.value,),
        ).fetchone()
        if row is None:
            return None
        return _to_caption(row)

    def all(self) -> tuple[Caption, ...]:
        cursor = self._connection.execute(
            "SELECT key, photo_ids, text, model, created_at, refused FROM captions ORDER BY rowid"
        )
        return tuple(_to_caption(row) for row in cursor)


def _to_subjects(row: tuple[Any, ...]) -> SubjectExtraction:
    key, labels, model, created_at, refused = row
    return SubjectExtraction(
        key=CaptionKey(key),
        labels=tuple(json.loads(labels)),
        model=model,
        created_at=datetime.fromisoformat(created_at),
        refused=refused,
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
                " (key, labels, model, created_at, refused)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    reading.key.value,
                    json.dumps(list(reading.labels)),
                    reading.model,
                    reading.created_at.isoformat(),
                    reading.refused,
                ),
            )

    def get(self, key: CaptionKey) -> SubjectExtraction | None:
        row = self._connection.execute(
            "SELECT key, labels, model, created_at, refused FROM subjects WHERE key = ?",
            (key.value,),
        ).fetchone()
        if row is None:
            return None
        return _to_subjects(row)

    def all(self) -> tuple[SubjectExtraction, ...]:
        cursor = self._connection.execute(
            "SELECT key, labels, model, created_at, refused FROM subjects ORDER BY rowid"
        )
        return tuple(_to_subjects(row) for row in cursor)
