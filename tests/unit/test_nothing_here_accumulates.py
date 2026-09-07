"""Everything derived can be thrown away and rebuilt identically.

Written to answer a question from the orchestrator: is the long horizon
-- year-scale trends, a changing picture of somebody -- this library's
work, or does it want a separate engine that *learns*?

The answer is that it is this library's, **and the reason is this
file**. A system that accumulates a model of a person has to be trusted
about what is in that model, because nobody can check it. This one
accumulates nothing: every derivation is rebuilt from the readings, so
the two-year picture is a function of the evidence and not a residue of
having run.

That is a claim, and a claim of that size should be checked rather than
written in a document.

## What is evidence and what is derived

    evidence     photographs, captions, notes, pages, days, screens,
                 corrections, and the kept readings -- append-only, and
                 the only thing a rebuild may not touch
    derived      stops, outings, anchors, themes, the profile, the
                 insights, the graph -- deleted and rebuilt here

A kept profile is **evidence**, not a model: it is a reading somebody
deliberately took on a day, and the trend between two of them is
arithmetic on two observations. Nothing carries a number forward from
one run into the next.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.graph import SqliteEvidenceGraph
from kiseki.adapters.sqlite.store import (
    SqlitePhotoRepository,
    SqliteSingleCaptionRepository,
    connect,
)
from kiseki.config.paths import resolve_paths
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.evidence.graph import Node, NodeKind, part_of
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint
from kiseki.interfaces.cli import EXIT_OK, main

BASE = datetime(2026, 3, 1, 23, 30, tzinfo=UTC)

DERIVED_TABLES = (
    "graph_edge_evidence",
    "graph_edges",
    "graph_nodes",
    "graph_meta",
    "stop_photos",
    "stops",
    "outings",
    "anchors",
    "theme_sets",
)
"""Everything a rebuild may throw away. Checked against the schema
below, so a derived table added later is either listed here or fails
the test that says the list is complete."""

EVIDENCE_TABLES = (
    "photos",
    "captions",
    "single_captions",
    "screen_readings",
    "note_readings",
    "page_readings",
    "daily_activity",
    "daily_input",
    "subjects",
    "profiles",
    "corrections",
)
"""What a rebuild must not touch. A kept profile is here rather than
above: it is a reading somebody deliberately took, and a trend between
two of them is arithmetic on two observations."""


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _a_library(tmp_path: Path) -> None:
    """Twenty nights at home, and a place returned to that is not home.

    Both are needed, and both need several photographs apiece: a lone
    shot at a point reads as transit rather than a stay. The second
    place is visited on four days: enough to be returned to, and
    fewer than the five that would make it an anchor too. A place
    inside an anchor is excluded from the
    interests on purpose -- frequent presence around home is
    circumstance rather than choice -- so a library with one place
    derives nothing and would prove nothing here.
    """
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    SqlitePhotoRepository(connection).save_all(
        [
            PhotoObservation(
                photo_id=PhotoId(f"sha256:{day:02d}{shot}"),
                captured_at=BASE + timedelta(days=day, minutes=shot * 20),
                location=GeoPoint(35.011637 + shot * 1e-5, 135.768123),
            )
            for day in range(20)
            for shot in range(3)
        ]
        + [
            PhotoObservation(
                photo_id=PhotoId(f"sha256:away{day}{shot}"),
                captured_at=BASE.replace(hour=13) + timedelta(days=day * 3, minutes=shot * 20),
                location=GeoPoint(35.031637, 135.788123),
            )
            for day in range(4)
            for shot in range(3)
        ]
    )
    singles = SqliteSingleCaptionRepository(connection)
    for day in range(20):
        singles.save(
            SingleCaption(
                PhotoId(f"sha256:{day:02d}0"),
                "a bowl of ramen on a wooden counter",
                "vl",
                BASE + timedelta(days=day),
            )
        )
    connection.close()
    assert main(["--data-root", str(tmp_path), "build"]) == EXIT_OK


def _graph_of(tmp_path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    graph = SqliteEvidenceGraph(connect(paths.db_path)).all()
    return (
        tuple(f"{node.id}|{node.kind.value}|{node.label}|{node.source}" for node in graph.nodes),
        tuple(f"{edge.id}|{edge.kind}" for edge in graph.edges),
    )


def _rows(tmp_path: Path, table: str) -> int:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    try:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        connection.close()


class TestThrowItAwayAndBuildItAgain:
    def test_the_graph_comes_back_identical(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The claim, checked: the picture is a function of the evidence
        and not a residue of having run."""
        _a_library(tmp_path)
        assert main(["--data-root", str(tmp_path), "graph", "--build"]) == EXIT_OK
        before = _graph_of(tmp_path)
        assert before[0], "an empty graph would prove nothing"

        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        connection = connect(paths.db_path)
        for table in DERIVED_TABLES:
            connection.execute(f"DELETE FROM {table}")
        connection.commit()
        connection.close()

        assert main(["--data-root", str(tmp_path), "build"]) == EXIT_OK
        assert main(["--data-root", str(tmp_path), "graph", "--build"]) == EXIT_OK
        capsys.readouterr()
        assert _graph_of(tmp_path) == before

    def test_the_evidence_is_untouched_by_a_rebuild(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A rebuild that lost a photograph would be one nobody could
        undo."""
        _a_library(tmp_path)
        before = {table: _rows(tmp_path, table) for table in EVIDENCE_TABLES}
        assert before["photos"] == 72
        assert main(["--data-root", str(tmp_path), "build"]) == EXIT_OK
        capsys.readouterr()
        assert {table: _rows(tmp_path, table) for table in EVIDENCE_TABLES} == before

    def test_building_the_graph_twice_changes_nothing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Not merely stable: the same rows, so a consumer keyed on what
        we write sees no news where nothing happened."""
        _a_library(tmp_path)
        main(["--data-root", str(tmp_path), "graph", "--build"])
        first = _graph_of(tmp_path)
        main(["--data-root", str(tmp_path), "graph", "--build"])
        capsys.readouterr()
        assert _graph_of(tmp_path) == first
        assert _rows(tmp_path, "graph_nodes") == len(first[0])


class TestARebuildForgetsWhatItNoLongerProduces:
    """The hole in the class above, found by changing the builder.

    Those tests delete the derived tables before rebuilding, which is
    not what anybody does: `kiseki graph --build` runs against whatever
    is already stored. `save` is additive on purpose -- a producer must
    not delete another's work -- so a node the builder **stopped**
    emitting stayed for ever, and nine of them did.

    A rebuild replaces. That is the only reason the class above is true
    of a real library rather than of a scrubbed one."""

    def test_a_node_the_builder_stops_making_is_forgotten(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _a_library(tmp_path)
        assert main(["--data-root", str(tmp_path), "graph", "--build"]) == EXIT_OK
        capsys.readouterr()

        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        store = SqliteEvidenceGraph(connect(paths.db_path))
        store.save(
            part_of(
                [
                    Node(
                        id="left:over",
                        kind=NodeKind.OBSERVATION,
                        label="something an older builder made",
                        source="photograph",
                    )
                ],
                [],
            )
        )
        assert "left:over" in {node.id for node in store.all().nodes}

        assert main(["--data-root", str(tmp_path), "graph", "--build"]) == EXIT_OK
        capsys.readouterr()
        assert "left:over" not in {node.id for node in store.all().nodes}

    def test_the_rebuild_is_still_everything_it_should_hold(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Replacing is only right if it replaces with the whole thing;
        an empty graph would also pass the test above."""
        _a_library(tmp_path)
        main(["--data-root", str(tmp_path), "graph", "--build"])
        before = _graph_of(tmp_path)
        main(["--data-root", str(tmp_path), "graph", "--build"])
        capsys.readouterr()
        assert _graph_of(tmp_path) == before
        assert before[0]


class TestTheTwoListsAreTheWholeDatabase:
    """The lists above are a claim about what this library holds, so a
    table added later has to be put in one of them on purpose."""

    def test_every_table_is_evidence_or_derived(self, tmp_path: Path) -> None:
        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        connection = connect(paths.db_path)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        connection.close()
        bookkeeping = {"schema_version", "sqlite_sequence"}
        undecided = tables - set(DERIVED_TABLES) - set(EVIDENCE_TABLES) - bookkeeping
        assert not undecided, (
            f"these are neither evidence nor derived: {sorted(undecided)}. "
            "A table that is neither is a place a model could accumulate "
            "without anybody noticing."
        )

    def test_nothing_is_in_both_lists(self) -> None:
        assert not set(DERIVED_TABLES) & set(EVIDENCE_TABLES)


class TestWhatThisDoesNotClaim:
    def test_a_kept_reading_survives_a_rebuild(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A kept profile is evidence, not a model: somebody took that
        reading on that day, and a rebuild cannot take it again
        (ADR-0070)."""
        _a_library(tmp_path)
        assert main(["--data-root", str(tmp_path), "profile", "--keep"]) == EXIT_OK
        kept = _rows(tmp_path, "profiles")
        assert kept == 1
        assert main(["--data-root", str(tmp_path), "build"]) == EXIT_OK
        capsys.readouterr()
        assert _rows(tmp_path, "profiles") == kept
