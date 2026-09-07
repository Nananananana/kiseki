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
    Edge,
    EdgeKind,
    EvidenceGraph,
    Node,
    NodeKind,
    graph_of,
)

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _fact(name: str = "f1") -> Node:
    return Node(id=name, kind=NodeKind.FACT, label="a photograph of a bowl", occurred_at=WHEN)


def _interest(name: str = "i1") -> Node:
    return Node(id=name, kind=NodeKind.INTEREST, label="eating")


def _conclusion(name: str = "c1") -> Node:
    return Node(id=name, kind=NodeKind.CONCLUSION, label="eating is rising")


class TestAConclusionReachesAFact:
    """Not a weak conclusion -- one this library could not have produced."""

    def test_a_conclusion_resting_on_a_fact_through_an_interest_is_held(self) -> None:
        graph = graph_of(
            [_conclusion(), _interest(), _fact()],
            [
                Edge("c1", "i1", EdgeKind.DERIVED_FROM),
                Edge("i1", "f1", EdgeKind.RESTS_ON),
            ],
        )
        assert [node.id for node in graph.facts_under("c1")] == ["f1"]

    def test_a_conclusion_that_reaches_nothing_is_refused(self) -> None:
        with pytest.raises(ValueError, match="reaches no fact"):
            EvidenceGraph(nodes=(_conclusion(),))

    def test_a_conclusion_that_stops_at_an_interest_is_refused(self) -> None:
        """An interest with nothing under it is the same failure one
        step further along."""
        with pytest.raises(ValueError, match="reaches no fact"):
            graph_of(
                [_conclusion(), _interest()],
                [Edge("c1", "i1", EdgeKind.DERIVED_FROM)],
            )

    def test_an_interest_with_no_evidence_is_allowed_on_its_own(self) -> None:
        """Only a conclusion makes the claim that needs support. An
        interest is refused by its own derivation, not by this."""
        assert graph_of([_interest()], []).of_kind(NodeKind.INTEREST)

    def test_a_long_chain_still_ends_at_the_reading(self) -> None:
        graph = graph_of(
            [_conclusion(), _interest("i1"), _interest("i2"), _fact("f9")],
            [
                Edge("c1", "i1", EdgeKind.DERIVED_FROM),
                Edge("i1", "i2", EdgeKind.RESTS_ON),
                Edge("i2", "f9", EdgeKind.RESTS_ON),
            ],
        )
        assert [node.id for node in graph.facts_under("c1")] == ["f9"]

    def test_a_cycle_does_not_hang_the_walk(self) -> None:
        """Nothing guarantees a graph assembled from several derivations
        is acyclic, and a traversal that assumed it would hang rather
        than fail."""
        graph = graph_of(
            [_conclusion(), _interest("i1"), _interest("i2"), _fact()],
            [
                Edge("c1", "i1", EdgeKind.DERIVED_FROM),
                Edge("i1", "i2", EdgeKind.RESTS_ON),
                Edge("i2", "i1", EdgeKind.RESTS_ON),
                Edge("i2", "f1", EdgeKind.RESTS_ON),
            ],
        )
        assert [node.id for node in graph.facts_under("c1")] == ["f1"]


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
            EvidenceGraph(nodes=(_fact(),), edges=(Edge("f1", "nowhere", EdgeKind.ABOUT),))

    def test_two_nodes_cannot_share_an_id(self) -> None:
        with pytest.raises(ValueError, match="share the id"):
            EvidenceGraph(nodes=(_fact("same"), _interest("same")))

    def test_a_thing_is_not_derived_from_itself(self) -> None:
        with pytest.raises(ValueError, match="derived from itself"):
            Edge("i1", "i1", EdgeKind.RESTS_ON)

    def test_a_node_that_cannot_be_named_is_refused(self) -> None:
        with pytest.raises(ValueError, match="cannot be named"):
            Node(id="f1", kind=NodeKind.FACT, label="   ")

    def test_the_same_edge_named_twice_is_stored_once(self) -> None:
        """Two derivations naming the same evidence is normal and says
        nothing extra; the second copy would make a count wrong."""
        graph = graph_of(
            [_interest(), _fact()],
            [
                Edge("i1", "f1", EdgeKind.RESTS_ON),
                Edge("i1", "f1", EdgeKind.RESTS_ON),
            ],
        )
        assert len(graph.edges) == 1

    def test_two_kinds_of_edge_between_one_pair_are_both_kept(self) -> None:
        graph = graph_of(
            [_interest(), _fact()],
            [
                Edge("i1", "f1", EdgeKind.RESTS_ON),
                Edge("i1", "f1", EdgeKind.ABOUT),
            ],
        )
        assert len(graph.edges) == 2


class TestWalkingIt:
    def test_a_node_nobody_stored_is_an_error_rather_than_an_empty_answer(self) -> None:
        """Silence would read as *this rests on nothing*, which is a
        different and much worse claim."""
        with pytest.raises(KeyError, match="not in this graph"):
            EvidenceGraph().facts_under("c1")

    def test_the_facts_come_back_in_a_fixed_order(self) -> None:
        graph = graph_of(
            [_conclusion(), _fact("f2"), _fact("f1"), _fact("f3")],
            [
                Edge("c1", "f2", EdgeKind.DERIVED_FROM),
                Edge("c1", "f1", EdgeKind.DERIVED_FROM),
                Edge("c1", "f3", EdgeKind.DERIVED_FROM),
            ],
        )
        assert [node.id for node in graph.facts_under("c1")] == ["f1", "f2", "f3"]

    def test_neighbours_are_the_edges_at_either_end(self) -> None:
        graph = graph_of(
            [_conclusion(), _interest(), _fact()],
            [
                Edge("c1", "i1", EdgeKind.DERIVED_FROM),
                Edge("i1", "f1", EdgeKind.RESTS_ON),
            ],
        )
        assert len(graph.neighbours("i1")) == 2

    def test_an_empty_library_says_so_rather_than_erring(self) -> None:
        assert EvidenceGraph().empty is True
