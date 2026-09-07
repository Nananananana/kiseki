"""The evidence graph, kept between runs (#435).

Three things carry the weight, and only the first is obvious.

A graph written and read back is the same graph, including the parts
that are easy to lose in a column: `None` distinguished from zero, the
metadata a producer put there, the drawing hints.

A neighbourhood is a **piece** and says so, because a conclusion three
steps from its observations still rests on them in storage, and a view
that cannot see them must not be read as one that rests on nothing.

And the neighbourhood read does not load the whole graph -- checked by
counting rows read, not by trusting the query, because the read that
stops scaling first is the one that silently became `SELECT *`.
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.graph import SqliteEvidenceGraph
from kiseki.adapters.sqlite.store import connect
from kiseki.domain.evidence.graph import (
    Edge,
    EvidenceGraph,
    Node,
    NodeKind,
    graph_of,
    part_of,
)
from kiseki.domain.evidence.visual import EdgeVisual, NodeVisual

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


@pytest.fixture
def store(tmp_path: Path) -> SqliteEvidenceGraph:
    """Through `connect`, because the tables are the schema's and a
    repository that made its own would let a database gain them
    without the version saying so."""
    return SqliteEvidenceGraph(connect(tmp_path / "kiseki.sqlite3"))


def _observation(name: str, source: str = "photograph") -> Node:
    return Node(
        id=name,
        kind=NodeKind.OBSERVATION,
        label=f"a reading called {name}",
        source=source,
        occurred_at=WHEN,
    )


def _chain() -> EvidenceGraph:
    """conclusion -> interest -> observation, the shape of the whole point."""
    return graph_of(
        [
            Node(id="c1", kind=NodeKind.CONCLUSION, label="eating is rising"),
            Node(id="i1", kind=NodeKind.INTEREST, label="eating"),
            _observation("o1", source="audio"),
        ],
        [
            Edge(id="r1", source="c1", target="i1", kind="derived_from"),
            Edge(id="r2", source="i1", target="o1", kind="rests_on"),
        ],
    )


class TestWhatGoesInComesOut:
    def test_a_graph_survives_the_round_trip(self, store: SqliteEvidenceGraph) -> None:
        store.save(_chain())
        back = store.all()
        assert {node.id for node in back.nodes} == {"c1", "i1", "o1"}
        assert [node.id for node in back.observations_under("c1")] == ["o1"]

    def test_the_source_of_a_reading_survives(self, store: SqliteEvidenceGraph) -> None:
        """The field that was missing for two releases (#438)."""
        store.save(_chain())
        assert store.all().sources_under("c1") == ("audio",)

    def test_nothing_scored_stays_nothing_rather_than_becoming_zero(
        self, store: SqliteEvidenceGraph
    ) -> None:
        """A node nobody scored and a node scored zero are different,
        and a column that turns the first into the second loses the
        difference silently."""
        store.save(
            graph_of(
                [
                    _observation("o1"),
                    Node(
                        id="o2", kind=NodeKind.OBSERVATION, label="x", source="note", confidence=0.0
                    ),
                ],
                [],
            )
        )
        found = {node.id: node for node in store.all().nodes}
        assert found["o1"].confidence is None
        assert found["o2"].confidence == 0.0

    def test_what_a_producer_knew_and_we_did_not_survives(self, store: SqliteEvidenceGraph) -> None:
        """The extension point: a field costs no migration."""
        store.save(
            graph_of(
                [
                    Node(
                        id="o1",
                        kind=NodeKind.OBSERVATION,
                        label="a recording",
                        source="audio",
                        metadata={"seconds": 42, "channels": 2},
                    )
                ],
                [],
            )
        )
        assert store.all().nodes[0].metadata == {"seconds": 42, "channels": 2}

    def test_the_drawing_hints_survive(self, store: SqliteEvidenceGraph) -> None:
        store.save(
            graph_of(
                [
                    Node(
                        id="o1",
                        kind=NodeKind.OBSERVATION,
                        label="a long sentence",
                        source="audio",
                        visual=NodeVisual(short_label="the park", group="outings", weight=0.6),
                    )
                ],
                [],
            )
        )
        visual = store.all().nodes[0].visual
        assert visual is not None
        assert (visual.short_label, visual.group, visual.weight) == ("the park", "outings", 0.6)

    def test_an_edge_keeps_its_reasons_and_its_evidence(self, store: SqliteEvidenceGraph) -> None:
        store.save(
            graph_of(
                [
                    _observation("o1"),
                    _observation("o2"),
                    Node(id="i1", kind=NodeKind.INTEREST, label="eating"),
                ],
                [
                    Edge(
                        id="r1",
                        source="i1",
                        target="o1",
                        kind="rests_on",
                        strength=0.82,
                        confidence=0.76,
                        evidence=("o2",),
                        because=("temporal proximity", "repeated behaviour"),
                        visual=EdgeVisual(weight=0.7),
                    )
                ],
            )
        )
        edge = store.all().edges[0]
        assert (edge.strength, edge.confidence) == (0.82, 0.76)
        assert edge.evidence == ("o2",)
        assert edge.because == ("temporal proximity", "repeated behaviour")
        assert edge.visual is not None
        assert edge.visual.weight == 0.7


class TestWritingIsAdditive:
    def test_a_second_producer_does_not_delete_the_first(self, store: SqliteEvidenceGraph) -> None:
        """A producer that knows about photographs writes what it knows
        without deleting what the recorder wrote."""
        store.save(graph_of([_observation("o1", "photograph")], []))
        store.save(graph_of([_observation("o2", "audio")], []))
        assert store.all().sources == ("audio", "photograph")

    def test_saving_the_same_node_twice_updates_it(self, store: SqliteEvidenceGraph) -> None:
        store.save(graph_of([_observation("o1")], []))
        store.save(
            graph_of(
                [Node(id="o1", kind=NodeKind.OBSERVATION, label="corrected", source="note")], []
            )
        )
        nodes = store.all().nodes
        assert len(nodes) == 1
        assert (nodes[0].label, nodes[0].source) == ("corrected", "note")

    def test_one_claim_cannot_be_stored_twice(self, store: SqliteEvidenceGraph) -> None:
        """The rule the domain applies in memory, made impossible here
        rather than merely discouraged."""
        store.save(_chain())
        with pytest.raises(sqlite3.IntegrityError):
            store._connection.execute(
                "INSERT INTO graph_edges (id, source_id, target_id, kind)"
                " VALUES ('other', 'i1', 'o1', 'rests_on')"
            )

    def test_forgetting_a_node_takes_its_edges_with_it(self, store: SqliteEvidenceGraph) -> None:
        store.save(_chain())
        assert store.forget(["o1"]) == 1
        nodes, edges = store.count()
        assert (nodes, edges) == (2, 1)

    def test_forgetting_nothing_is_not_an_error(self, store: SqliteEvidenceGraph) -> None:
        assert store.forget([]) == 0


class TestANeighbourhoodIsAPiece:
    def test_it_says_it_is_not_the_whole_graph(self, store: SqliteEvidenceGraph) -> None:
        store.save(_chain())
        assert store.around("c1", steps=1).whole is False
        assert store.all().whole is True

    def test_a_conclusion_cut_off_from_its_readings_is_not_refused(
        self, store: SqliteEvidenceGraph
    ) -> None:
        """One step from the conclusion reaches the interest and not the
        observation. That conclusion still rests on a reading in
        storage, so a view that cannot see it must not be read as one
        that rests on nothing -- and must not raise, which is what a
        whole graph would do."""
        store.save(_chain())
        near = store.around("c1", steps=1)
        assert {node.id for node in near.nodes} == {"c1", "i1"}
        assert near.observations_under("c1") == ()

    def test_two_steps_reach_the_reading(self, store: SqliteEvidenceGraph) -> None:
        store.save(_chain())
        assert {node.id for node in store.around("c1", steps=2).nodes} == {"c1", "i1", "o1"}

    def test_no_steps_is_the_node_alone(self, store: SqliteEvidenceGraph) -> None:
        store.save(_chain())
        assert {node.id for node in store.around("c1", steps=0).nodes} == {"c1"}

    def test_it_walks_edges_in_both_directions(self, store: SqliteEvidenceGraph) -> None:
        """A reader asking about an observation wants what was concluded
        from it, and the arrows point the other way."""
        store.save(_chain())
        assert {node.id for node in store.around("o1", steps=1).nodes} == {"o1", "i1"}

    def test_a_negative_neighbourhood_is_refused(self, store: SqliteEvidenceGraph) -> None:
        with pytest.raises(ValueError, match="negative number of steps"):
            store.around("c1", steps=-1)


class TestItDoesNotReadTheWholeGraphToAnswerASmallQuestion:
    """Counted rather than trusted: the read that stops scaling first is
    the one that quietly became a full scan."""

    def _many(self, store: SqliteEvidenceGraph) -> None:
        nodes = [_observation(f"o{index}", "photograph") for index in range(200)]
        nodes.append(Node(id="i1", kind=NodeKind.INTEREST, label="eating"))
        store.save(graph_of(nodes, [Edge(id="r0", source="i1", target="o0", kind="rests_on")]))

    def test_a_neighbourhood_reads_a_handful_of_rows(self, store: SqliteEvidenceGraph) -> None:
        self._many(store)
        seen: list[str] = []
        store._connection.set_trace_callback(seen.append)
        near = store.around("i1", steps=1)
        store._connection.set_trace_callback(None)
        assert {node.id for node in near.nodes} == {"i1", "o0"}
        assert not any("FROM graph_nodes WHERE 1 = 1" in statement for statement in seen), seen

    def test_counting_reads_no_rows_at_all(self, store: SqliteEvidenceGraph) -> None:
        self._many(store)
        assert store.count() == (201, 1)


class TestTheSchemaSaysWhatItHolds:
    def test_every_column_a_node_has_is_a_column(self, store: SqliteEvidenceGraph) -> None:
        """`metadata` is the extension point and everything else is
        typed: anything a query filters on graduates to a column."""
        columns = {
            row[1] for row in store._connection.execute("PRAGMA table_info(graph_nodes)").fetchall()
        }
        assert {"id", "kind", "label", "source", "occurred_at", "confidence"} <= columns

    def test_the_backwards_walk_has_an_index(self, store: SqliteEvidenceGraph) -> None:
        """The read this whole structure exists for."""
        indexes = {
            row[1] for row in store._connection.execute("PRAGMA index_list(graph_edges)").fetchall()
        }
        assert "graph_edges_target" in indexes

    def test_metadata_is_stored_as_json_a_person_can_read(self, store: SqliteEvidenceGraph) -> None:
        store.save(
            graph_of(
                [
                    Node(
                        id="o1",
                        kind=NodeKind.OBSERVATION,
                        label="a recording",
                        source="audio",
                        metadata={"note": "ラーメン"},
                    )
                ],
                [],
            )
        )
        stored = store._connection.execute(
            "SELECT metadata FROM graph_nodes WHERE id = 'o1'"
        ).fetchone()[0]
        assert json.loads(stored) == {"note": "ラーメン"}
        assert "ラーメン" in stored, "escaped unicode is unreadable in a database browser"


class TestAPieceIsStillChecked:
    def test_a_piece_still_refuses_an_edge_pointing_at_nothing(self) -> None:
        """Only the rule about conclusions is skipped; every structural
        check holds of any subgraph."""
        with pytest.raises(ValueError, match="not in the graph"):
            part_of([_observation("o1")], [Edge(id="r1", source="o1", target="gone", kind="about")])


class TestAnOlderLibraryGainsThemAndLosesNothing:
    """Opening a database that predates the graph, checked end to end.

    Proved once against a copy of the owner's real library, which was
    at schema 9: it walked 9 to 10 to 11 and kept all 4,950
    photographs. This is that, in a form that runs every time.

    What each half does, since the test cannot tell them apart and
    should not pretend to: `connect` runs the schema, which creates
    every table that is missing, and the migration moves the version.
    The migration also names its own tables -- redundantly, as every
    migration here does -- so that a person reading it sees what
    changed without reading the schema too. Removing that line breaks
    nothing and is still worth keeping.
    """

    def _a_version_ten_database(self, tmp_path: Path) -> Path:
        """A database as it was before the graph existed."""
        where = tmp_path / "older.sqlite3"
        connection = connect(where)
        connection.execute(
            "INSERT INTO photos (id, captured_at) VALUES ('sha256:aa', '2026-06-01T12:00:00')"
        )
        for table in ("graph_edge_evidence", "graph_edges", "graph_nodes", "graph_meta"):
            connection.execute(f"DROP TABLE {table}")
        connection.execute("UPDATE schema_version SET version = 10")
        connection.commit()
        connection.close()
        return where

    def test_the_tables_arrive_and_the_version_moves(self, tmp_path: Path) -> None:
        where = self._a_version_ten_database(tmp_path)
        connection = connect(where)
        (version,) = connection.execute("SELECT version FROM schema_version").fetchone()
        assert version == 12
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'graph%'"
            ).fetchall()
        }
        assert tables == {"graph_nodes", "graph_edges", "graph_edge_evidence", "graph_meta"}

    def test_what_was_already_stored_is_still_there(self, tmp_path: Path) -> None:
        """Additive and explicit: a migration that lost a photograph
        would be a migration nobody could undo."""
        where = self._a_version_ten_database(tmp_path)
        connection = connect(where)
        (count,) = connection.execute("SELECT COUNT(*) FROM photos").fetchone()
        assert count == 1

    def test_the_graph_is_usable_immediately_after(self, tmp_path: Path) -> None:
        where = self._a_version_ten_database(tmp_path)
        store = SqliteEvidenceGraph(connect(where))
        assert store.count() == (0, 0)
        store.save(_chain())
        assert store.all().sources_under("c1") == ("audio",)

    def test_reopening_a_migrated_database_does_not_migrate_again(self, tmp_path: Path) -> None:
        where = self._a_version_ten_database(tmp_path)
        connect(where).close()
        connection = connect(where)
        assert connection.execute("SELECT version FROM schema_version").fetchone()[0] == 12
