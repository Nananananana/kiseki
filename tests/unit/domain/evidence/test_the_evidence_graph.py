"""Why the library concluded something, as a thing a program can walk.

Phase 1 of the evidence graph (`docs/proposals/0010`, #435). The
provenance was always kept; it was a tuple of strings inside a row,
which a person can read and a program cannot traverse.

Two rules carry the weight here. Every conclusion reaches a fact, so
one resting on nothing observed is refused rather than stored. And no
node carries a coordinate, because a graph is a document written for
another program -- which is exactly the shape of thing that wrote the
owner's doorstep at full precision the week before this was written
(ADR-0095).
"""

from datetime import UTC, datetime

import pytest
from kiseki.domain.evidence.graph import (
    EDGE_KINDS,
    Edge,
    EvidenceGraph,
    Node,
    NodeKind,
    graph_of,
)
from kiseki.domain.evidence.visual import NodeVisual

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _edge(source: str, target: str, kind: str) -> Edge:
    """An edge with an id made from its own ends, so a test reads as
    the claim it is making rather than as bookkeeping."""
    return Edge(id=f"{source}-{kind}-{target}", source=source, target=target, kind=kind)


def _observation(name: str = "f1", source: str = "photograph") -> Node:
    return Node(
        id=name,
        kind=NodeKind.OBSERVATION,
        label="a bowl of ramen",
        source=source,
        occurred_at=WHEN,
    )


def _interest(name: str = "i1") -> Node:
    return Node(id=name, kind=NodeKind.INTEREST, label="eating")


def _conclusion(name: str = "c1") -> Node:
    return Node(id=name, kind=NodeKind.CONCLUSION, label="eating is rising")


class TestAConclusionReachesAnObservation:
    """Not a weak conclusion -- one this library could not have produced."""

    def test_a_conclusion_resting_on_a_fact_through_an_interest_is_held(self) -> None:
        graph = graph_of(
            [_conclusion(), _interest(), _observation()],
            [
                _edge("c1", "i1", "derived_from"),
                _edge("i1", "f1", "rests_on"),
            ],
        )
        assert [node.id for node in graph.observations_under("c1")] == ["f1"]

    def test_a_conclusion_that_reaches_nothing_is_refused(self) -> None:
        with pytest.raises(ValueError, match="reaches no observation"):
            EvidenceGraph(nodes=(_conclusion(),))

    def test_a_conclusion_that_stops_at_an_interest_is_refused(self) -> None:
        """An interest with nothing under it is the same failure one
        step further along."""
        with pytest.raises(ValueError, match="reaches no observation"):
            graph_of(
                [_conclusion(), _interest()],
                [_edge("c1", "i1", "derived_from")],
            )

    def test_an_interest_with_no_evidence_is_allowed_on_its_own(self) -> None:
        """Only a conclusion makes the claim that needs support. An
        interest is refused by its own derivation, not by this."""
        assert graph_of([_interest()], []).of_kind(NodeKind.INTEREST)

    def test_a_long_chain_still_ends_at_the_reading(self) -> None:
        graph = graph_of(
            [_conclusion(), _interest("i1"), _interest("i2"), _observation("f9")],
            [
                _edge("c1", "i1", "derived_from"),
                _edge("i1", "i2", "rests_on"),
                _edge("i2", "f9", "rests_on"),
            ],
        )
        assert [node.id for node in graph.observations_under("c1")] == ["f9"]

    def test_a_cycle_does_not_hang_the_walk(self) -> None:
        """Nothing guarantees a graph assembled from several derivations
        is acyclic, and a traversal that assumed it would hang rather
        than fail."""
        graph = graph_of(
            [_conclusion(), _interest("i1"), _interest("i2"), _observation()],
            [
                _edge("c1", "i1", "derived_from"),
                _edge("i1", "i2", "rests_on"),
                _edge("i2", "i1", "rests_on"),
                _edge("i2", "f1", "rests_on"),
            ],
        )
        assert [node.id for node in graph.observations_under("c1")] == ["f1"]


class TestAnySourceAtAll:
    """A source is a fact about the world, so it is not a closed set.

    This library learned that expensively: the web shipped in v0.11,
    `source_of` fell through to its photograph default for two
    releases, and an answer resting on what the owner wrote and read
    reported *read from photograph*. A closed vocabulary did not
    prevent an unknown source; it made one indistinguishable from a
    camera."""

    @pytest.mark.parametrize(
        "source",
        [
            "photograph",
            "note",
            "page",
            "audio",
            "video",
            "day_at_the_keys",
            "something_nobody_has_written_yet",
        ],
    )
    def test_a_fact_may_come_from_anything(self, source: str) -> None:
        node = Node(id="f1", kind=NodeKind.OBSERVATION, label="something observed", source=source)
        assert node.source == source

    def test_a_fact_that_does_not_say_where_it_came_from_is_refused(self) -> None:
        """The failure this design exists to prevent: an unnamed
        source silently becoming a photograph."""
        with pytest.raises(ValueError, match="does not say what it came from"):
            Node(id="f1", kind=NodeKind.OBSERVATION, label="something observed")

    def test_a_derivation_has_no_source_of_its_own(self) -> None:
        """It comes from the facts under it, which is what the edges
        are for."""
        assert _interest().source is None

    def test_a_source_that_is_not_a_name_is_refused(self) -> None:
        """Open in membership, not in shape: a vocabulary that admits
        `Photograph` and `photograph` is two vocabularies."""
        with pytest.raises(ValueError, match="shape of a source name"):
            Node(id="f1", kind=NodeKind.OBSERVATION, label="x", source="Audio Recording")

    def test_a_conclusion_says_which_witnesses_it_rests_on(self) -> None:
        """The question a reader asks before believing it."""
        graph = graph_of(
            [
                _conclusion(),
                _interest(),
                _observation("f1", source="audio"),
                _observation("f2", source="note"),
                _observation("f3", source="audio"),
            ],
            [
                _edge("c1", "i1", "derived_from"),
                _edge("i1", "f1", "rests_on"),
                _edge("i1", "f2", "rests_on"),
                _edge("i1", "f3", "rests_on"),
            ],
        )
        assert graph.sources_under("c1") == ("audio", "note")

    def test_the_graph_lists_the_sources_it_holds_rather_than_a_fixed_set(self) -> None:
        graph = graph_of(
            [_observation("f1", source="audio"), _observation("f2", source="photograph")], []
        )
        assert graph.sources == ("audio", "photograph")
        assert [node.id for node in graph.of_source("audio")] == ["f1"]


class TestAnObservationIsNotAnEvent:
    """A photograph at the park, a recording made there and a line
    written that evening are three readings of one afternoon. A model
    that cannot say so counts the afternoon three times or throws two
    of the readings away."""

    def _afternoon(self) -> EvidenceGraph:
        return graph_of(
            [
                Node(
                    id="e1",
                    kind=NodeKind.EVENT,
                    label="an afternoon at the park",
                    occurred_at=WHEN,
                ),
                _observation("o1", source="photograph"),
                _observation("o2", source="audio"),
                _observation("o3", source="note"),
            ],
            [
                _edge("e1", "o1", "derived_from"),
                _edge("e1", "o2", "derived_from"),
                _edge("e1", "o3", "derived_from"),
            ],
        )

    def test_three_readings_can_be_one_afternoon(self) -> None:
        graph = self._afternoon()
        assert len(graph.of_kind(NodeKind.EVENT)) == 1
        assert len(graph.observations_under("e1")) == 3

    def test_the_event_names_every_witness_to_it(self) -> None:
        """Cross-modal evidence: a conclusion that does not depend on
        one source can say so."""
        assert self._afternoon().sources_under("e1") == (
            "audio",
            "note",
            "photograph",
        )

    def test_an_event_has_no_source_of_its_own(self) -> None:
        """What it came from is the observations under it, which is
        structure rather than a field and so cannot fall out of step
        with the edges."""
        event = Node(id="e1", kind=NodeKind.EVENT, label="an afternoon")
        assert event.source is None

    def test_one_reading_may_witness_several_events(self) -> None:
        """A recording that covers leaving home, a train and a film is
        one source and several events."""
        graph = graph_of(
            [
                Node(id="e1", kind=NodeKind.EVENT, label="leaving home"),
                Node(id="e2", kind=NodeKind.EVENT, label="a train"),
                _observation("o1", source="audio"),
            ],
            [
                _edge("e1", "o1", "derived_from"),
                _edge("e2", "o1", "derived_from"),
            ],
        )
        assert len(graph.of_kind(NodeKind.EVENT)) == 2
        assert graph.observations_under("e2")[0].id == "o1"

    def test_a_conclusion_may_reach_its_readings_through_an_event(self) -> None:
        graph = graph_of(
            [
                _conclusion(),
                Node(id="e1", kind=NodeKind.EVENT, label="an afternoon"),
                _observation("o1", source="audio"),
            ],
            [
                _edge("c1", "e1", "derived_from"),
                _edge("e1", "o1", "derived_from"),
            ],
        )
        assert graph.sources_under("c1") == ("audio",)


class TestAnythingMayPointAtAnything:
    """No edge is restricted by the kinds at its ends. A graph whose
    shape were decided by today's derivations would have to be
    migrated by every one that follows."""

    def test_a_fact_may_precede_another_observation(self) -> None:
        graph = graph_of(
            [_observation("f1", source="audio"), _observation("f2", source="page")],
            [_edge("f1", "f2", "precedes")],
        )
        assert len(graph.edges) == 1

    def test_a_relationship_nobody_declared_is_refused(self) -> None:
        """Adding one is a line in EDGE_KINDS, so that every type in
        the graph can be listed."""
        with pytest.raises(ValueError, match="not a declared relationship"):
            _edge("f1", "f2", "vibes_with")

    def test_causation_is_not_among_them(self) -> None:
        """Correlation is not causation, and a causal claim is a
        hypothesis rather than an edge."""
        assert "causes" not in EDGE_KINDS

    def test_a_producer_may_carry_what_only_it_knows(self) -> None:
        """The extension point: a field costs no migration, and
        anything a query filters on should graduate to a column."""
        node = Node(
            id="f1",
            kind=NodeKind.OBSERVATION,
            label="a recording",
            source="audio",
            metadata={"seconds": 42},
        )
        assert node.metadata["seconds"] == 42


class TestNoNodeCarriesACoordinate:
    """A place is the most sensitive node here by a distance, and the
    rule lives in the constructor because a serving boundary can be
    bypassed by a second caller."""

    @pytest.mark.parametrize(
        "label",
        [
            "34.756612,135.461234",
            "place:34.76,135.46",
            "returned to near 35.0116, 135.7681",
            "-33.868820,151.209290",
        ],
        ids=["a bare pair", "a place reference", "a sentence", "the southern hemisphere"],
    )
    def test_a_label_that_says_where_is_refused(self, label: str) -> None:
        with pytest.raises(ValueError, match="may not carry a coordinate"):
            Node(id="p1", kind=NodeKind.ENTITY, label=label)

    def test_a_blurred_coordinate_is_refused_too(self) -> None:
        """Two decimals still names a kilometre square, and a graph is
        read by whoever holds it rather than by the owner."""
        with pytest.raises(ValueError, match="may not carry a coordinate"):
            Node(id="p1", kind=NodeKind.ENTITY, label="34.76,135.46")

    def test_a_place_named_the_way_grounding_names_one_is_held(self) -> None:
        node = Node(
            id="place-1",
            kind=NodeKind.ENTITY,
            label="Place 1: returned to on 12 separate days, about every 7 days",
        )
        assert node.label.startswith("Place 1")

    def test_a_number_that_is_not_a_pair_passes(self) -> None:
        """A count and a share are not a coordinate, and refusing them
        would make the rule unusable."""
        assert Node(id="e1", kind=NodeKind.ENTITY, label="seen on 12 days, 0.75 of them at night")


class TestTheShapeIsChecked:
    def test_an_edge_pointing_at_nothing_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not in the graph"):
            EvidenceGraph(nodes=(_observation(),), edges=(_edge("f1", "nowhere", "about"),))

    def test_two_nodes_cannot_share_an_id(self) -> None:
        with pytest.raises(ValueError, match="share the id"):
            EvidenceGraph(nodes=(_observation("same"), _interest("same")))

    def test_a_thing_is_not_derived_from_itself(self) -> None:
        with pytest.raises(ValueError, match="derived from itself"):
            _edge("i1", "i1", "rests_on")

    def test_a_node_that_cannot_be_named_is_refused(self) -> None:
        with pytest.raises(ValueError, match="cannot be named"):
            Node(id="f1", kind=NodeKind.OBSERVATION, label="   ")

    def test_the_same_edge_named_twice_is_stored_once(self) -> None:
        """Two derivations naming the same evidence is normal and says
        nothing extra; the second copy would make a count wrong."""
        graph = graph_of(
            [_interest(), _observation()],
            [
                _edge("i1", "f1", "rests_on"),
                _edge("i1", "f1", "rests_on"),
            ],
        )
        assert len(graph.edges) == 1

    def test_two_kinds_of_edge_between_one_pair_are_both_kept(self) -> None:
        graph = graph_of(
            [_interest(), _observation()],
            [
                _edge("i1", "f1", "rests_on"),
                _edge("i1", "f1", "about"),
            ],
        )
        assert len(graph.edges) == 2


class TestAnEdgeIsAClaim:
    """Not plumbing between two records. *A influenced B* is a thing the
    library thinks and can be wrong about, so it carries its own
    identity, strength, evidence and reasons."""

    def test_an_edge_carries_why_it_was_drawn(self) -> None:
        edge = Edge(
            id="r1",
            source="e1",
            target="i1",
            kind="influences",
            strength=0.82,
            confidence=0.76,
            because=("temporal proximity", "repeated behaviour"),
        )
        assert edge.because[0] == "temporal proximity"

    def test_strength_and_confidence_are_different_questions(self) -> None:
        """A weak relationship seen fifty times and a strong one seen
        twice are different claims, and one number cannot say both."""
        edge = Edge(
            id="r1",
            source="a",
            target="b",
            kind="influences",
            strength=0.2,
            confidence=0.9,
        )
        assert (edge.strength, edge.confidence) == (0.2, 0.9)

    def test_an_edge_without_an_id_cannot_be_revised_later(self) -> None:
        with pytest.raises(ValueError, match="cannot be revised"):
            Edge(id=" ", source="a", target="b", kind="related_to")

    def test_two_edges_cannot_share_an_id(self) -> None:
        with pytest.raises(ValueError, match="share the id"):
            EvidenceGraph(
                nodes=(_observation("o1"), _observation("o2"), _interest()),
                edges=(
                    Edge(id="r1", source="i1", target="o1", kind="rests_on"),
                    Edge(id="r1", source="i1", target="o2", kind="rests_on"),
                ),
            )

    def test_an_edge_citing_something_absent_is_refused(self) -> None:
        """The field version of a conclusion reaching no observation:
        evidence that is not in the graph cannot be checked."""
        with pytest.raises(ValueError, match="does not hold it"):
            EvidenceGraph(
                nodes=(_observation("o1"), _interest()),
                edges=(
                    Edge(
                        id="r1",
                        source="i1",
                        target="o1",
                        kind="rests_on",
                        evidence=("o9",),
                    ),
                ),
            )

    def test_evidence_the_graph_holds_is_kept(self) -> None:
        graph = EvidenceGraph(
            nodes=(_observation("o1"), _observation("o2"), _interest()),
            edges=(
                Edge(
                    id="r1",
                    source="i1",
                    target="o1",
                    kind="rests_on",
                    evidence=("o2",),
                ),
            ),
        )
        assert graph.edges[0].evidence == ("o2",)

    def test_a_strength_outside_the_range_is_refused(self) -> None:
        with pytest.raises(ValueError, match="strength"):
            Edge(id="r1", source="a", target="b", kind="related_to", strength=1.4)

    def test_a_confidence_outside_the_range_is_refused(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            Edge(id="r1", source="a", target="b", kind="related_to", confidence=-0.1)


class TestDrawingIsNotReasoning:
    """The hints travel with the node so two models cannot drift, and
    nothing in the reasoning reads them."""

    def test_a_node_may_carry_a_hint_for_a_viewer(self) -> None:
        node = Node(
            id="o1",
            kind=NodeKind.OBSERVATION,
            label="a long sentence a derivation wrote",
            source="audio",
            visual=NodeVisual(short_label="the park", group="outings", weight=0.6),
        )
        assert node.visual is not None
        assert node.visual.short_label == "the park"

    def test_no_position_and_no_colour_are_ours_to_decide(self) -> None:
        """A position is a layout imposed on every viewer and a colour is
        a palette; what a viewer needs from us is what things are."""
        assert not hasattr(NodeVisual(), "position")
        assert not hasattr(NodeVisual(), "colour")

    def test_a_weight_outside_a_share_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not a share"):
            NodeVisual(weight=1.5)

    def test_the_reasoning_never_reads_a_drawing_hint(self) -> None:
        """Checkable, and the whole rule: the graph module may hold the
        field and must never branch on it."""
        from inspect import getsource

        from kiseki.domain.evidence import graph as module

        for line in getsource(module).splitlines():
            stripped = line.strip()
            if stripped.startswith(("#", "visual:")) or stripped.startswith('"""'):
                continue
            assert ".visual." not in stripped, line


class TestWalkingIt:
    def test_a_node_nobody_stored_is_an_error_rather_than_an_empty_answer(self) -> None:
        """Silence would read as *this rests on nothing*, which is a
        different and much worse claim."""
        with pytest.raises(KeyError, match="not in this graph"):
            EvidenceGraph().observations_under("c1")

    def test_the_facts_come_back_in_a_fixed_order(self) -> None:
        graph = graph_of(
            [_conclusion(), _observation("f2"), _observation("f1"), _observation("f3")],
            [
                _edge("c1", "f2", "derived_from"),
                _edge("c1", "f1", "derived_from"),
                _edge("c1", "f3", "derived_from"),
            ],
        )
        assert [node.id for node in graph.observations_under("c1")] == ["f1", "f2", "f3"]

    def test_neighbours_are_the_edges_at_either_end(self) -> None:
        graph = graph_of(
            [_conclusion(), _interest(), _observation()],
            [
                _edge("c1", "i1", "derived_from"),
                _edge("i1", "f1", "rests_on"),
            ],
        )
        assert len(graph.neighbours("i1")) == 2

    def test_an_empty_library_says_so_rather_than_erring(self) -> None:
        assert EvidenceGraph().empty is True
