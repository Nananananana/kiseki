"""Asking the library why it concluded something (#435).

The question the whole structure exists to answer. A reader who doubts
a conclusion is handed the readings under it rather than a score.

The test that matters most is the last one: a conclusion three steps
from its readings must still reach them, because `why` reads a
neighbourhood rather than the whole graph and a walk one step too short
would answer *nothing* to a question that has an answer.
"""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.graph import SqliteEvidenceGraph
from kiseki.adapters.sqlite.store import connect
from kiseki.config.paths import resolve_paths
from kiseki.domain.evidence.graph import Edge, Node, NodeKind, graph_of
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _seed(tmp_path: Path) -> None:
    """A conclusion resting on two witnesses, through an interest."""
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    store = SqliteEvidenceGraph(connect(paths.db_path))
    store.save(
        graph_of(
            [
                Node(id="c1", kind=NodeKind.CONCLUSION, label="flight is new", confidence=0.9),
                Node(id="i1", kind=NodeKind.INTEREST, label="flight"),
                Node(
                    id="o1",
                    kind=NodeKind.OBSERVATION,
                    label="a screen reading the library read",
                    source="screen",
                    occurred_at=WHEN,
                ),
                Node(
                    id="o2",
                    kind=NodeKind.OBSERVATION,
                    label="a note the library read",
                    source="note",
                    occurred_at=WHEN + timedelta(days=3),
                ),
            ],
            [
                Edge(
                    id="e1",
                    source="c1",
                    target="i1",
                    kind="derived_from",
                    because=("trend", "lifecycle"),
                ),
                Edge(id="e2", source="i1", target="o1", kind="rests_on"),
                Edge(id="e3", source="i1", target="o2", kind="rests_on"),
            ],
        )
    )


def _run(tmp_path: Path, *rest: str) -> int:
    return main(["--data-root", str(tmp_path), *rest])


class TestItAnswersTheQuestion:
    def test_it_names_the_readings_and_the_witnesses(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert _run(tmp_path, "why", "c1") == EXIT_OK
        said = capsys.readouterr().out
        assert "rests on       2 readings" in said
        assert "note, screen" in said

    def test_a_reading_says_when_it_was_made(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """*These two screens* is a list; *these two screens, over a
        fortnight in August* is a reason."""
        _seed(tmp_path)
        assert _run(tmp_path, "why", "c1") == EXIT_OK
        assert "2026-06-01" in capsys.readouterr().out

    def test_it_says_why_the_edge_was_drawn(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert _run(tmp_path, "why", "c1") == EXIT_OK
        assert "because        trend, lifecycle" in capsys.readouterr().out

    def test_the_document_carries_the_readings(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert _run(tmp_path, "why", "c1", "--json") == EXIT_OK
        document = json.loads(capsys.readouterr().out)
        assert document["schema"] == "kiseki-why"
        assert document["sources"] == ["note", "screen"]
        assert {reading["id"] for reading in document["rests_on"]} == {"o1", "o2"}

    def test_a_node_nobody_stored_is_a_named_failure(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Not an empty answer, which would read as *this rests on
        nothing* -- a different and much worse claim."""
        _seed(tmp_path)
        assert _run(tmp_path, "why", "nowhere") == EXIT_BAD_INPUT
        assert capsys.readouterr().err.startswith("NothingStored: ")

    def test_the_walk_is_long_enough_to_reach_the_readings(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`why` reads a neighbourhood rather than the whole graph, so a
        walk one step too short would answer *nothing* to a question
        that has an answer. The conclusion here is two steps from its
        readings, which is how deep this library's chains go."""
        _seed(tmp_path)
        assert _run(tmp_path, "why", "c1", "--json") == EXIT_OK
        assert len(json.loads(capsys.readouterr().out)["rests_on"]) == 2


class TestTheGraphCommand:
    def test_an_unbuilt_graph_says_what_would_fill_it(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert _run(tmp_path, "graph") == EXIT_OK
        assert "graph --build" in capsys.readouterr().out

    def test_building_it_writes_what_is_derived(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert _run(tmp_path, "graph", "--build") == EXIT_OK
        assert "built" in capsys.readouterr().out

    def test_it_counts_by_role(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _seed(tmp_path)
        assert _run(tmp_path, "graph") == EXIT_OK
        said = capsys.readouterr().out
        assert "observation  2" in said
        assert "conclusion   1" in said

    def test_the_document_is_nodes_and_edges(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The shape a viewer asked for."""
        _seed(tmp_path)
        assert _run(tmp_path, "graph", "--json") == EXIT_OK
        document = json.loads(capsys.readouterr().out)
        assert document["schema"] == "kiseki-graph"
        assert len(document["nodes"]) == 4
        assert len(document["edges"]) == 3

    def test_the_document_says_whether_it_is_the_whole_graph(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A viewer that drew a piece as if it were everything would
        show a conclusion resting on less than it does."""
        _seed(tmp_path)
        assert _run(tmp_path, "graph", "--json") == EXIT_OK
        assert json.loads(capsys.readouterr().out)["whole"] is True

    def test_it_needs_no_model(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An orchestrator deciding whether to give this library a GPU
        can read the whole of its reasoning first."""
        monkeypatch.setenv("KISEKI_MODEL_USE", "withheld")
        assert _run(tmp_path, "graph", "--build") == EXIT_OK
        capsys.readouterr()


class TestNoCoordinateLeavesThisWay:
    def test_the_document_needs_no_blurring_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A document with no dangerous field is better than one with a
        dangerous field and a careful default (ADR-0095). A node may not
        carry a coordinate at all, so there is nothing here to coarsen."""
        _seed(tmp_path)
        assert _run(tmp_path, "graph", "--json") == EXIT_OK
        written = capsys.readouterr().out
        assert "raw" not in written
        assert "blur" not in written
