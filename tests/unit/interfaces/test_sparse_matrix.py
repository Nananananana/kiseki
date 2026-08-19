"""Every source may be absent, and the whole library still answers.

The matrix seeds a library with every kind of evidence, then removes
one kind and runs every deterministic command against what is left. A
command that crashes, or that reports failure because a source it does
not need is missing, fails here rather than in front of a reader whose
library happens to lack it. See ADR-0063.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import (
    SqliteCaptionRepository,
    SqlitePhotoRepository,
    SqliteProfileRepository,
    SqliteScreenshotReadingRepository,
    SqliteSingleCaptionRepository,
    SqliteSubjectRepository,
    connect,
)
from kiseki.config.paths import resolve_paths
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.domain.shared.geo import GeoPoint
from kiseki.interfaces.cli import EXIT_OK, main

NOW = datetime.now(UTC)
HOME = GeoPoint(34.7810, 135.4690)
AWAY = GeoPoint(35.0116, 135.7681)

COMMANDS: tuple[tuple[str, ...], ...] = (
    ("report",),
    ("profile",),
    ("places",),
    ("trips",),
    ("suggest",),
    ("trend",),
    ("lifecycle",),
    ("insights",),
    ("discover",),
    ("compare",),
    ("drift",),
    ("privacy",),
    ("doctor",),
    ("retention",),
    ("export",),
    ("corrections",),
    ("reread",),
    ("retry",),
)

OMISSIONS = (
    "nothing",
    "photograph",
    "journey",
    "stay caption",
    "single caption",
    "screen reading",
    "kept reading",
)


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _seed(tmp_path: Path) -> None:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    photographs = []
    index = 0
    for week in range(10):
        when = NOW - timedelta(days=7 * week)
        for offset in range(3):
            index += 1
            photographs.append(
                PhotoObservation(
                    PhotoId(f"sha256:p{index:04d}"),
                    when + timedelta(minutes=12 * offset),
                    HOME,
                    thumbnail_ref=f"demo/{index}.jpg",
                    content_kind="photo",
                )
            )
        for offset in range(2):
            index += 1
            photographs.append(
                PhotoObservation(
                    PhotoId(f"sha256:p{index:04d}"),
                    when + timedelta(hours=5, minutes=15 * offset),
                    AWAY,
                    thumbnail_ref=f"demo/{index}.jpg",
                    content_kind="photo",
                )
            )
    screens = []
    for week in range(6):
        index += 1
        identifier = PhotoId(f"sha256:s{index:04d}")
        screens.append(
            PhotoObservation(
                identifier,
                NOW - timedelta(days=7 * week + 1),
                None,
                content_kind="screenshot",
            )
        )
    SqlitePhotoRepository(connection).save_all(photographs + screens)

    captions = SqliteCaptionRepository(connection)
    subjects = SqliteSubjectRepository(connection)
    for topic, photo in (("ramen", photographs[0]), ("museum", photographs[3])):
        key = CaptionKey.of([photo.photo_id])
        captions.save(
            Caption(
                key=key,
                photo_ids=(photo.photo_id,),
                text=f"a photograph of {topic}",
                model="demo",
                created_at=NOW,
            )
        )
        subjects.save(SubjectExtraction(key=key, labels=(topic,), model="demo", created_at=NOW))
    singles = SqliteSingleCaptionRepository(connection)
    singles.save(
        SingleCaption(
            photo_id=photographs[6].photo_id,
            text="a bowl of noodles",
            model="demo",
            created_at=NOW,
        )
    )
    readings = SqliteScreenshotReadingRepository(connection)
    for shot in screens:
        readings.save(
            ScreenshotReading(
                photo_id=shot.photo_id,
                category="map",
                labels=("route",),
                model="demo",
                created_at=NOW,
            )
        )
    profiles = SqliteProfileRepository(connection)
    for days in (60, 30, 1):
        at = NOW - timedelta(days=days)
        profiles.save(
            Profile(
                generated_at=at,
                interests=(
                    Interest(
                        topic="ramen",
                        score=0.6,
                        confidence=0.5,
                        evidence=(
                            InterestEvidence(
                                kind=EvidenceKind.PHOTOGRAPH,
                                reference="caption:seed",
                                observed_at=at,
                            ),
                        ),
                        first_seen=at,
                        last_seen=at,
                    ),
                ),
            )
        )
    connection.close()
    assert main(["--data-root", str(tmp_path), "build"]) == EXIT_OK


def _remove(tmp_path: Path, omission: str) -> None:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    statements = {
        "nothing": [],
        # A stop is made of photographs, so a library without them has no
        # journeys either. Leaving the stops behind would ask a question no
        # real library can be asked, and the answer would teach nothing.
        "photograph": [
            "DELETE FROM photos",
            "DELETE FROM stop_photos",
            "DELETE FROM stops",
            "DELETE FROM outings",
        ],
        "journey": ["DELETE FROM outings", "DELETE FROM stops"],
        "stay caption": ["DELETE FROM captions", "DELETE FROM subjects"],
        "single caption": ["DELETE FROM single_captions"],
        "screen reading": ["DELETE FROM screen_readings"],
        "kept reading": ["DELETE FROM profiles"],
    }[omission]
    with connection:
        for statement in statements:
            try:
                connection.execute(statement)
            except Exception:
                continue
    connection.close()


@pytest.mark.parametrize("omission", OMISSIONS)
def test_the_library_answers_without(tmp_path: Path, omission: str) -> None:
    _seed(tmp_path)
    _remove(tmp_path, omission)
    failures: list[str] = []
    for command in COMMANDS:
        try:
            code = main(["--data-root", str(tmp_path), *command])
        except Exception as error:
            failures.append(f"{command[0]} raised {type(error).__name__}: {error}")
            continue
        if code != EXIT_OK:
            failures.append(f"{command[0]} exited {code}")
    assert failures == [], f"without {omission}: " + "; ".join(failures)
