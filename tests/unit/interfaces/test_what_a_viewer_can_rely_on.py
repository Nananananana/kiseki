"""What the orchestrator asked for before it starts drawing (R-G1 to R-G6).

Six requirements, written while there was still nothing to see, on the
argument that they are cheaper before the design than after. Four were
already true; two were not, and one of those was a latent defect.

The two that carry the most weight here:

**Support and contradiction share one array.** With two arrays, or two
calls, the shorter code is the one that shows only the supporting half
-- and every consumer writes the shorter code eventually, not from
malice. The shape is settled now, while there is nothing to contradict
and it costs a word.

**A label is written here, never copied.** No node carries anything the
owner wrote, said or photographed, so a screen may show a label without
asking which privacy level produced it. Checked rather than declared:
the owner's own words go into every field the builder touches, and the
test fails if any of them reaches a node.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from kiseki.application.graph_building import ALGORITHM_VERSION, build_graph
from kiseki.domain.evidence.visual import EdgeVisual, NodeVisual
from kiseki.domain.insight import Insight, InsightDirection, InsightKind, InsightReport
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence, Profile
from kiseki.interfaces.cli import EXIT_OK, main

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)

HIS_OWN_WORDS = "the ramen at the place by the river, with Yuki, on her birthday"
"""Something only the owner could have written. If any part of it
reaches a node, a screen showing labels has shown it."""


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _library_full_of_his_words() -> tuple[Profile, InsightReport]:
    """Every field the builder touches, carrying the owner's own words."""
    evidence = (
        InterestEvidence(
            kind=EvidenceKind.NOTE,
            reference=f"note:{HIS_OWN_WORDS}",
            observed_at=WHEN,
        ),
    )
    profile = Profile(
        generated_at=WHEN,
        interests=(
            Interest(
                topic="eating",
                score=0.7,
                confidence=0.8,
                evidence=evidence,
                first_seen=WHEN,
                last_seen=WHEN,
            ),
        ),
    )
    insights = InsightReport(
        oldest_at=WHEN,
        latest_at=WHEN,
        insights=(
            Insight(
                topic="eating",
                kind=InsightKind.RISING,
                direction=next(iter(InsightDirection)),
                magnitude=1.0,
                first_seen=WHEN,
                last_seen=WHEN,
                confidence=0.6,
                evidence=(f"caption:{HIS_OWN_WORDS}",),
                novelty=0.5,
                derived_from=("kiseki insights",),
            ),
        ),
    )
    return profile, insights


class TestALabelIsWrittenNeverCopied:
    """R-G5, answered by construction rather than by declaration."""

    def test_no_label_carries_a_word_the_owner_wrote(self) -> None:
        graph = build_graph(*_library_full_of_his_words())
        for node in graph.nodes:
            assert HIS_OWN_WORDS not in node.label
            assert "Yuki" not in node.label
            assert "birthday" not in node.label

    def test_a_label_says_the_kind_of_witness_instead(self) -> None:
        """*a note the library read* -- which is what a screen needs and
        all it needs."""
        graph = build_graph(*_library_full_of_his_words())
        labels = {node.label for node in graph.nodes}
        assert any("note" in label for label in labels)

    def test_an_id_may_still_be_a_reference_the_producer_chose(self) -> None:
        """The line is drawn at the label, which is what gets shown. An
        id is an identifier the producer already published, and a screen
        that displayed raw ids would be showing keys, not content."""
        graph = build_graph(*_library_full_of_his_words())
        assert any(HIS_OWN_WORDS in node.id for node in graph.nodes)


class TestSupportAndContradictionShareOneArray:
    """R-G1, settled before there is anything to contradict."""

    def _seeded(self, tmp_path: Path) -> None:
        main(["--data-root", str(tmp_path), "graph", "--build"])

    def test_every_entry_says_what_it_does_to_the_thing_above_it(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from kiseki.adapters.sqlite.graph import SqliteEvidenceGraph
        from kiseki.adapters.sqlite.store import connect
        from kiseki.config.paths import resolve_paths

        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        SqliteEvidenceGraph(connect(paths.db_path)).save(build_graph(*_library_full_of_his_words()))
        capsys.readouterr()
        assert main(["--data-root", str(tmp_path), "why", "interest:eating", "--json"]) == EXIT_OK
        document = json.loads(capsys.readouterr().out)
        assert document["evidence"], "nothing to check, so this would prove nothing"
        for entry in document["evidence"]:
            assert entry["stance"] == "supports"
            assert "node_id" in entry
            assert "at" in entry

    def test_there_is_no_second_array_to_forget(self) -> None:
        """The whole point. A screen cannot show half of this by
        writing less code."""
        from kiseki.interfaces.payloads import why_payload

        graph = build_graph(*_library_full_of_his_words())
        document = why_payload(graph, "interest:eating")
        arrays = [key for key, value in document.items() if isinstance(value, list)]
        assert "evidence" in arrays
        assert not [key for key in arrays if "contradict" in key or "support" in key]


class TestTheDocumentSaysWhichRulesBuiltIt:
    """R-G6. A hypothesis that appeared because the owner did something
    new, and one that appeared because these rules learned to look
    somewhere else, are different news."""

    def test_a_built_graph_carries_the_version(self) -> None:
        assert build_graph(*_library_full_of_his_words()).built_by == ALGORITHM_VERSION

    def test_it_survives_a_round_trip_through_storage(self, tmp_path: Path) -> None:
        """Stored beside the graph rather than stamped on at read time:
        a graph read back was built by whatever version was current
        then, not now."""
        from kiseki.adapters.sqlite.graph import SqliteEvidenceGraph
        from kiseki.adapters.sqlite.store import connect
        from kiseki.config.paths import resolve_paths

        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        store = SqliteEvidenceGraph(connect(paths.db_path))
        store.save(build_graph(*_library_full_of_his_words()))
        assert store.all().built_by == ALGORITHM_VERSION

    def test_the_document_carries_it(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "graph", "--build", "--json"]) == EXIT_OK
        assert json.loads(capsys.readouterr().out)["built_by"] == ALGORITHM_VERSION


class TestTheSameStateWritesTheSameDocument:
    """R-G6 again, and the part that was a latent defect: nothing
    promised the order of the nodes."""

    def test_the_nodes_come_out_in_id_order(self, tmp_path: Path) -> None:
        """The promise, asserted directly. Reading twice and finding
        the same thing is not enough: SQLite returns rows in rowid
        order, so a handful of nodes written in id order comes back
        in id order whether anything asked for it or not. These are
        written in the reverse."""
        from kiseki.adapters.sqlite.graph import SqliteEvidenceGraph
        from kiseki.adapters.sqlite.store import connect
        from kiseki.config.paths import resolve_paths
        from kiseki.domain.evidence.graph import Node, NodeKind, graph_of

        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        store = SqliteEvidenceGraph(connect(paths.db_path))
        store.save(
            graph_of(
                [
                    Node(
                        id=name,
                        kind=NodeKind.OBSERVATION,
                        label="a reading",
                        source="note",
                    )
                    for name in ("zebra", "yak", "xerus", "walrus", "vole")
                ],
                [],
            )
        )
        ids = [node.id for node in store.all().nodes]
        assert ids == sorted(ids), ids

    def test_two_reads_are_byte_identical(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["--data-root", str(tmp_path), "graph", "--build"])
        capsys.readouterr()
        main(["--data-root", str(tmp_path), "graph", "--json"])
        first = capsys.readouterr().out
        main(["--data-root", str(tmp_path), "graph", "--json"])
        assert capsys.readouterr().out == first

    def test_a_vacuum_does_not_reorder_it(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """SQLite happened to return rows in rowid order and nothing
        promised it; a VACUUM is enough to change that. A consumer keyed
        on the hash of what we write would read a reordering as
        *something happened today*."""
        from kiseki.adapters.sqlite.graph import SqliteEvidenceGraph
        from kiseki.adapters.sqlite.store import connect
        from kiseki.config.paths import resolve_paths

        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        store = SqliteEvidenceGraph(connect(paths.db_path))
        store.save(build_graph(*_library_full_of_his_words()))
        capsys.readouterr()
        main(["--data-root", str(tmp_path), "graph", "--json"])
        before = capsys.readouterr().out

        connection = connect(paths.db_path)
        connection.execute("VACUUM")
        connection.close()

        main(["--data-root", str(tmp_path), "graph", "--json"])
        assert capsys.readouterr().out == before


class TestNothingInADrawingHintMeansAnything:
    """R-G4. A hint that carries meaning is a second place the document
    says something, and then one document draws two pictures."""

    def test_an_edge_hint_holds_only_size_and_a_name(self) -> None:
        """`dashed` meant *offered rather than settled*, which is a fact
        about the claim and belongs in the edge. It is gone."""
        fields = set(vars(EdgeVisual()))
        assert fields == {"short_label", "weight"}

    def test_a_node_hint_holds_only_size_grouping_and_a_name(self) -> None:
        assert set(vars(NodeVisual())) == {"short_label", "group", "weight"}

    def test_no_hint_carries_a_position_or_a_colour(self) -> None:
        """A position is a layout imposed on every viewer; a colour is
        somebody else's palette."""
        for hint in (NodeVisual(), EdgeVisual()):
            assert not [name for name in vars(hint) if name in {"position", "colour", "color"}]
