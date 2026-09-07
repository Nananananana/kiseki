"""Turning what the library already derived into a graph it can walk.

Two things carry the weight.

**A new source arrives for free.** The builder does not know what a
photograph is: it reads the reference a derivation stored and asks
`sourcing` what kind of witness that is. A recorder producing a prefix
nobody has seen gets nodes that say what it is, and the builder does
not change. That is tested with a source that does not exist.

**No coordinate becomes an id.** The library's own evidence references
are `place:34.756612,135.461234`, so a builder using a reference as an
id would put the owner's doorstep in the graph through the field nobody
was watching. Places get an opaque name, and `Node` refuses a
coordinate in an id as well as a label.
"""

from datetime import UTC, datetime

import pytest
from kiseki.application.graph_building import build_graph
from kiseki.domain.evidence.graph import Node, NodeKind
from kiseki.domain.insight import Insight, InsightDirection, InsightKind, InsightReport
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence, Profile

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)
DOORSTEP = "place:34.756612,135.461234"


def _interest(topic: str, *references: str, confidence: float = 0.8) -> Interest:
    return Interest(
        topic=topic,
        score=0.7,
        confidence=confidence,
        evidence=tuple(
            InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference=reference, observed_at=WHEN)
            for reference in references
        ),
        first_seen=WHEN,
        last_seen=WHEN,
    )


def _profile(*interests: Interest) -> Profile:
    return Profile(generated_at=WHEN, interests=interests)


def _insight(topic: str, *references: str) -> InsightReport:
    return InsightReport(
        oldest_at=WHEN,
        latest_at=WHEN,
        insights=(
            Insight(
                topic=topic,
                kind=next(iter(InsightKind)),
                direction=next(iter(InsightDirection)),
                magnitude=1.0,
                first_seen=WHEN,
                last_seen=WHEN,
                confidence=0.6,
                evidence=tuple(references),
                novelty=0.5,
                derived_from=("kiseki insights",),
            ),
        ),
    )


class TestNoCoordinateBecomesAnId:
    """The one thing this builder must be careful about."""

    def test_a_place_gets_an_opaque_name(self) -> None:
        """The entity is named; the reading of it is a day at it."""
        graph = build_graph(_profile(_interest("camping", DOORSTEP)), None)
        assert [node.id for node in graph.of_kind(NodeKind.ENTITY)] == ["place-1"]
        assert [node.id for node in graph.of_kind(NodeKind.OBSERVATION)] == [
            "visit:place-1:2026-06-01"
        ]

    def test_no_digit_of_the_doorstep_survives_anywhere(self) -> None:
        """Every field, because the leak would be through whichever one
        nobody was watching."""
        graph = build_graph(_profile(_interest("camping", DOORSTEP)), _insight("camping", DOORSTEP))
        written = repr(graph)
        assert "34.756612" not in written
        assert "135.461234" not in written

    def test_the_node_itself_refuses_a_coordinate_in_an_id(self) -> None:
        """Belt and braces, and the reason the builder can be simple."""
        with pytest.raises(ValueError, match="may not carry a coordinate"):
            Node(id=DOORSTEP, kind=NodeKind.OBSERVATION, label="a reading", source="photograph")

    def test_places_are_numbered_by_how_often_they_were_cited(self) -> None:
        """Stable across a rebuild as long as the evidence is, and the
        same ordering grounding uses when it says *Place 1*."""
        often = "place:34.10,135.10"
        seldom = "place:34.20,135.20"
        graph = build_graph(
            _profile(_interest("a", often, seldom), _interest("b", often)),
            None,
        )
        assert {node.id for node in graph.of_kind(NodeKind.ENTITY)} == {
            "place-1",
            "place-2",
        }
        # An interest whose topic is not a place needs no edge of its
        # own: the walk already answers *which places for this* --
        # interest -> rests_on -> a visit -> about -> the place.
        visits = {node.id for node in graph.observations_under("interest:b")}
        reached = {
            edge.target for edge in graph.edges if edge.source in visits and edge.kind == "about"
        }
        assert reached == {"place-1"}


class TestANewSourceArrivesForFree:
    """The builder does not know what a photograph is."""

    @pytest.mark.parametrize(
        ("reference", "expected"),
        [
            ("note:diary.md#3", "note"),
            ("page:a1b2c3", "page"),
            ("caption:aa", "stay_caption"),
            ("screen:aa", "screen"),
        ],
    )
    def test_a_reading_says_which_witness_it_came_from(self, reference: str, expected: str) -> None:
        graph = build_graph(_profile(_interest("reading", reference)), None)
        assert graph.of_kind(NodeKind.OBSERVATION)[0].source == expected

    def test_a_source_nobody_has_written_yet_still_gets_a_node(self) -> None:
        """It falls to the photograph default until its prefix is
        mapped, which is what the guard in test_a_note_is_not_a_photograph
        exists to notice -- but it is still a node with a source, not a
        node with nothing."""
        graph = build_graph(_profile(_interest("listening", "audio:recording-8")), None)
        node = graph.of_kind(NodeKind.OBSERVATION)[0]
        assert node.id == "audio:recording-8"
        assert node.source

    def test_several_witnesses_to_one_interest_are_all_kept(self) -> None:
        graph = build_graph(_profile(_interest("camping", "note:a", "page:b", "caption:c")), None)
        assert len(graph.of_kind(NodeKind.OBSERVATION)) == 3
        assert graph.sources_under("interest:camping") == ("note", "page", "stay_caption")


class TestWhatIsBuilt:
    def test_an_interest_rests_on_its_evidence(self) -> None:
        graph = build_graph(_profile(_interest("camping", "note:a")), None)
        assert [edge.kind for edge in graph.edges] == ["rests_on"]

    def test_a_conclusion_is_derived_from_its_evidence(self) -> None:
        graph = build_graph(None, _insight("camping", "note:a"))
        assert [edge.kind for edge in graph.edges] == ["derived_from"]

    def test_a_conclusion_says_why_it_was_drawn(self) -> None:
        graph = build_graph(None, _insight("camping", "note:a"))
        assert graph.edges[0].because == ("kiseki insights",)

    def test_the_confidence_a_derivation_computed_is_carried(self) -> None:
        """Carried, never synthesised: nothing here combines two."""
        graph = build_graph(_profile(_interest("camping", "note:a", confidence=0.42)), None)
        interest = graph.of_kind(NodeKind.INTEREST)[0]
        assert interest.confidence == 0.42

    def test_an_empty_library_builds_an_empty_graph(self) -> None:
        assert build_graph(None, None).empty is True

    def test_a_conclusion_with_no_evidence_cannot_be_built(self) -> None:
        """The invariant, reached through the builder: a conclusion
        resting on nothing observed is one this library could not have
        produced, so assembling one is a bug here rather than a row in
        the database."""
        with pytest.raises(ValueError, match="reaches no observation"):
            build_graph(None, _insight("camping"))


class TestBuildingTwiceIsNotDuplicating:
    def test_the_same_library_builds_the_same_ids(self) -> None:
        """A graph that grew a second copy of everything on each
        `refresh` would be useless within a week."""
        library = (
            _profile(_interest("camping", DOORSTEP, "note:a")),
            _insight("camping", "note:a"),
        )
        first = build_graph(*library)
        second = build_graph(*library)
        assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
        assert [edge.id for edge in first.edges] == [edge.id for edge in second.edges]

    def test_one_reading_cited_twice_is_one_node(self) -> None:
        graph = build_graph(_profile(_interest("a", "note:x"), _interest("b", "note:x")), None)
        assert len(graph.of_kind(NodeKind.OBSERVATION)) == 1
        assert len(graph.edges) == 2


class TestTheCasesTheRealLibraryFound:
    """Two things every synthetic test here missed, found on the first
    build against the owner's own library."""

    def test_a_topic_can_itself_be_a_place(self) -> None:
        """`place:34.7,135.4` is an ordinary interest in this library.
        The tests above all used topics like *camping*, which is what
        synthetic data is for and what it costs."""
        graph = build_graph(_profile(_interest(DOORSTEP, "note:a")), None)
        interest = graph.of_kind(NodeKind.INTEREST)[0]
        assert interest.id == "interest:place-1"
        assert "34.756612" not in interest.label

    def test_a_dormant_finding_reaches_the_reading_it_was_computed_over(self) -> None:
        """Twelve of the owner's six hundred insights cite no evidence,
        and every one is dormant -- a finding about an **absence**, so
        there is nothing recent to point at. `derived_from` already
        names the kept reading, so the graph was right to refuse them
        and the builder was wrong not to look."""
        dormant = InsightReport(
            oldest_at=WHEN,
            latest_at=WHEN,
            insights=(
                Insight(
                    topic="signs",
                    kind=InsightKind.DORMANT,
                    direction=next(iter(InsightDirection)),
                    magnitude=1.0,
                    first_seen=WHEN,
                    last_seen=WHEN,
                    confidence=0.4,
                    evidence=(),
                    novelty=0.5,
                    derived_from=("trend", "lifecycle", "profile:2026-08-29T13:50:34"),
                ),
            ),
        )
        graph = build_graph(None, dormant)
        assert graph.sources_under("insight:signs:dormant") == ("kept_reading",)

    def test_a_command_name_is_not_evidence_for_itself(self) -> None:
        """`derived_from` mixes readings with the names of derivations,
        and only one of those is a thing anybody can go and look at."""
        graph = build_graph(None, _insight("camping", "note:a"))
        observations = {node.id for node in graph.of_kind(NodeKind.OBSERVATION)}
        assert observations == {"note:a"}
        assert "trend" not in observations
        assert "kiseki insights" not in observations


class TestAReadingCarriesWhenItWasMade:
    """*These six screens* is a list; *these six screens, over a
    fortnight in August* is a reason. The first real answer read
    `undated` six times over."""

    def test_the_evidence_time_reaches_the_node(self) -> None:
        graph = build_graph(_profile(_interest("camping", "note:a")), None)
        assert graph.of_kind(NodeKind.OBSERVATION)[0].occurred_at == WHEN

    def test_a_finding_that_names_a_reading_without_a_time_leaves_it_undated(self) -> None:
        """`derived_from` names readings without saying when they were
        made, so those stay undated rather than being given a plausible
        time."""
        graph = build_graph(None, _insight("camping", "note:a"))
        assert graph.of_kind(NodeKind.OBSERVATION)[0].occurred_at is None


class TestAPlaceIsAThingVisitsAreAbout:
    """A returned-to place is cited by its interest twice, as the first
    visit and the last. Keying a node by the reference collapsed the two
    into one, so twenty-two of the owner's interests said *rests on one
    reading* when they rest on two, and the second date was gone."""

    def _place_interest(self) -> Profile:
        first = InterestEvidence(kind=EvidenceKind.VISIT, reference=DOORSTEP, observed_at=WHEN)
        last = InterestEvidence(
            kind=EvidenceKind.VISIT,
            reference=DOORSTEP,
            observed_at=WHEN.replace(month=8),
        )
        return Profile(
            generated_at=WHEN,
            interests=(
                Interest(
                    topic=DOORSTEP,
                    score=0.7,
                    confidence=0.8,
                    evidence=(first, last),
                    first_seen=WHEN,
                    last_seen=WHEN.replace(month=8),
                ),
            ),
        )

    def test_two_visits_to_one_place_are_two_readings(self) -> None:
        graph = build_graph(self._place_interest(), None)
        readings = graph.observations_under("interest:place-1")
        assert len(readings) == 2
        assert {node.occurred_at.month for node in readings if node.occurred_at} == {6, 8}

    def test_the_place_itself_is_an_entity(self) -> None:
        graph = build_graph(self._place_interest(), None)
        assert [node.id for node in graph.of_kind(NodeKind.ENTITY)] == ["place-1"]

    def test_the_visits_and_the_interest_point_at_it(self) -> None:
        """What makes *which places do I go to for this* a walk rather
        than a query somebody has to write (#391)."""
        graph = build_graph(self._place_interest(), None)
        pointing = {
            edge.source for edge in graph.edges if edge.kind == "about" and edge.target == "place-1"
        }
        assert "interest:place-1" in pointing
        assert len([item for item in pointing if item.startswith("visit:")]) == 2

    def test_a_finding_citing_a_place_rests_on_the_visits_to_it(self) -> None:
        """Not on the place. A finding cites the place, and what it
        rests on are the days at it -- pointing at the thing would
        have a conclusion rest on a concept rather than a reading."""
        graph = build_graph(self._place_interest(), _insight("camping", DOORSTEP, "note:a"))
        assert not [node for node in graph.nodes if node.id.endswith(":undated")]
        under = {node.id for node in graph.observations_under("insight:camping:new")}
        assert any(item.startswith("visit:place-1:") for item in under), under

    def test_an_entity_carries_no_coordinate(self) -> None:
        graph = build_graph(self._place_interest(), None)
        for node in graph.of_kind(NodeKind.ENTITY):
            assert "34.756612" not in node.id
            assert "34.756612" not in node.label
