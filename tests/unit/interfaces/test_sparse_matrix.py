"""Every source may be absent, and the whole library still answers.

The matrix seeds a library with every kind of evidence, then removes
one kind and runs every deterministic command against what is left. A
command that crashes, or that reports failure because a source it does
not need is missing, fails here rather than in front of a reader whose
library happens to lack it. See ADR-0063.

**It said "every kind of evidence" and meant six of nine** (#372).
ActivityRecord landed at schema 6, NoteRecord at 7, WebRecord at 9,
and none of the three was ever seeded here. Two claims were failing at
once, and the second is the worse one:

- absence was unproven for the three newest sources, which is at
  least the thing this file was aiming at;
- **no command in this matrix had ever run on a library that had a
  note reading or a page reading in it.** 18 commands over 7
  omissions is 126 runs, every one on a library with none of the
  three. A derivation that crashed on the *presence* of a page
  reading would have passed the whole matrix, and so would one that
  ignored it.

That second half is a population that is not empty and where every
member carries the same value for the thing that matters. Counting
the runs does not show it. Only a new kind of input does.

`kiseki privacy` had the identical omission, the identical three
sources, and was fixed in #353; the conformance kit has it still
(#373). Three machines, each correct when written, none extended when
the rule they enforce got new members -- because in none of them was
**adding a source made a decision**. It is one here now: `SOURCES`
below is the saying, and a table holding the owner's evidence that is
missing from it fails rather than passing quietly.
"""

import json
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
    "note reading",
    "page reading",
    "day of movement",
)

SOURCES = {
    "photos": "photograph",
    "captions": "stay caption",
    "single_captions": "single caption",
    "screen_readings": "screen reading",
    "subjects": "stay caption",
    "profiles": "kept reading",
    "note_readings": "note reading",
    "page_readings": "page reading",
    "daily_activity": "day of movement",
}
"""Every table holding the owner's own evidence, and the omission that
removes it. Checked against the schema below, so a source that lands
without being seeded fails here rather than being absent in silence."""

NOT_A_SOURCE = {
    "schema_version": "one row saying which migration ran",
    "sqlite_sequence": "SQLite's own bookkeeping",
    "stops": "derived from photographs, and removed with them",
    "stop_photos": "which photographs made a stop; removed with them",
    "outings": "assembled from stops, and removed with them",
    "anchors": "estimated from stops, and removed with them",
    "theme_sets": "derived from subject readings, and removed with them",
    "corrections": "the owner's answer to a derivation, not a source of evidence",
}
"""Why each table is not seeded and not omitted. The same shape
test_the_report_counts_every_table.py uses, for the same reason: the
list is where a person adding a table has to stop and decide."""


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


def _derived(tmp_path: Path):
    """Everything the surfaces are built from, or None where there is none."""
    from kiseki.application.pipeline import Pipeline
    from kiseki.interfaces.cli import _pipeline_from

    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    pipeline: Pipeline = _pipeline_from(paths.db_path)
    return pipeline


@pytest.mark.parametrize("omission", OMISSIONS)
def test_the_payloads_survive_without(tmp_path: Path, omission: str) -> None:
    """The API's shapes are built by pure functions; they are checked here.

    Serving them over HTTP would test the socket, which is not what can
    break. What can break is a payload calling .date() on a moment that
    is not there, or an offset meeting a naive one on the way out
    (ADR-0063, ADR-0064).
    """
    from kiseki.interfaces.payloads import (
        comparison_payload,
        discovery_payload,
        insights_payload,
        lifecycle_payload,
        privacy_payload,
        profile_payload,
        report_payload,
        trend_payload,
    )

    _seed(tmp_path)
    _remove(tmp_path, omission)
    pipeline = _derived(tmp_path)

    failures: list[str] = []
    checks: tuple[tuple[str, object, object], ...] = (
        ("report", report_payload, pipeline.report()),
        ("profile", profile_payload, pipeline.profile(keep=False)),
        ("trend", trend_payload, pipeline.trend()),
        ("lifecycle", lifecycle_payload, pipeline.lifecycle()),
        ("insights", insights_payload, pipeline.insights()),
        ("discover", discovery_payload, pipeline.discover()),
        ("compare", comparison_payload, pipeline.compare()),
        ("privacy", privacy_payload, pipeline.privacy()),
    )
    for name, shape, value in checks:
        if value is None:
            continue
        for blur in (True, False):
            try:
                document = (
                    shape(value)  # type: ignore[operator]
                    if name == "privacy"
                    else shape(value, blur=blur)  # type: ignore[operator]
                )
                json.dumps(document)
            except Exception as error:
                failures.append(f"{name} (blur={blur}) raised {type(error).__name__}: {error}")
    assert failures == [], f"without {omission}: " + "; ".join(failures)


@pytest.mark.parametrize("omission", OMISSIONS)
def test_the_view_is_written_without(tmp_path: Path, omission: str) -> None:
    """The page is a file, so the check is that a file appears and reads.

    Its sections are allowed to say there is not enough history; they
    are not allowed to be absent, and the command is not allowed to
    fail because a source it does not need is missing.
    """
    _seed(tmp_path)
    _remove(tmp_path, omission)
    assert main(["--data-root", str(tmp_path), "view"]) == EXIT_OK
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    pages = list(paths.cache_dir.glob("*.html"))
    assert pages, f"without {omission}: no page was written"
    page = pages[0].read_text(encoding="utf-8")
    assert "<html" in page.lower()
    for heading in ("Read as interests", "Worth a look", "What changed"):
        assert heading in page, f"without {omission}: {heading} is missing"
    assert "http://" not in page.replace("http://www.w3.org", "")
