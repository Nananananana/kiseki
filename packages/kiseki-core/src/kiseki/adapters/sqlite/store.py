"""SQLite storage.

Timestamps are stored as ISO 8601 text including the offset. SQLite has no date
type, and text sorts correctly for a fixed offset while keeping the offset
itself, which the contract requires.
"""

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.outing.outing import Outing, OutingId
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.time_range import TimeRange

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS photos (
    id           TEXT PRIMARY KEY,
    captured_at  TEXT NOT NULL,
    latitude     REAL,
    longitude    REAL
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
    elif stored[0] != SCHEMA_VERSION:
        connection.close()
        raise ValueError(f"database is at schema {stored[0]}, expected {SCHEMA_VERSION}")

    connection.commit()
    return connection


def _to_observation(row: tuple[Any, ...]) -> PhotoObservation:
    identifier, captured_at, latitude, longitude = row
    place = GeoPoint(latitude, longitude) if latitude is not None else None
    return PhotoObservation(PhotoId(identifier), datetime.fromisoformat(captured_at), place)


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
            )
            for item in observations
        ]
        with self._connection:
            self._connection.executemany(
                "INSERT OR REPLACE INTO photos (id, captured_at, latitude, longitude)"
                " VALUES (?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    def all(self) -> tuple[PhotoObservation, ...]:
        cursor = self._connection.execute(
            "SELECT id, captured_at, latitude, longitude FROM photos ORDER BY captured_at"
        )
        return tuple(_to_observation(row) for row in cursor)

    def between(self, start: datetime, end: datetime) -> tuple[PhotoObservation, ...]:
        cursor = self._connection.execute(
            "SELECT id, captured_at, latitude, longitude FROM photos"
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
