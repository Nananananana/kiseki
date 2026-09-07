"""Turning what the library already derived into a graph it can walk.

Nothing here derives anything. Every node is a reading or a derivation
that already exists, and every edge is a relationship the code already
had -- written down where a program can follow it instead of being
implicit in the order the pipeline runs.

    conclusion   an insight            derived_from  its evidence
    interest     a profile's interest  rests_on      its evidence
    observation  a stored reading      about         the place it names
    entity       a place                             named, never located

## A new source arrives for free

The point of the design, and worth stating because it is easy to lose.
This builder does not know what a photograph is. It reads the reference
a derivation stored -- `note:diary.md#3`, `page:a1b2c3`, `audio:...` --
and asks `sourcing` what kind of witness that is. A recorder that
starts producing interests with a prefix nobody has seen gets nodes
that say what it is, and this file does not change.

That only works because the prefix mapping is checked against the
source: `note:` and `page:` were missing from it for three releases and
everything they touched was reported as a photograph (#438).

## Places are named, never located

The one thing this file must be careful about. The library's own
evidence references are `place:34.756612,135.461234`, so using a
reference as a node id would put the owner's doorstep in the graph
through the field nobody was watching -- which is why `Node` refuses a
coordinate in an id as well as a label, and why places get an opaque
name here.

The naming is grounding's (ADR-0040): places are numbered by how often
they were returned to, so `place-1` is the same place across a rebuild
as long as the ordering is, and no digit of where it is survives.

A **topic** can be a place too -- `place:34.7,135.4` is an ordinary
interest here -- so topics are named alongside references. The first
build against the owner's real library found that; every synthetic
test had topics like *camping*, which is what synthetic data is for
and what it costs.

## A reading carries when it was made

`InterestEvidence` knows when it observed what it observed, and the
first real answer read *undated* six times over. A provenance that
cannot say when is half an answer: *these six screens* is a list,
and *these six screens, over a fortnight in August* is a reason.

Only the evidence carries it. A finding's `derived_from` names
readings without saying when they were made, so those stay undated
rather than being given a plausible time.

## A place is a thing, and a visit is a reading of it

The first version made a place an observation, which lost something
measurable: a returned-to place is cited by its interest **twice**,
as the first visit and the last, and keying a node by the reference
collapsed the two into one. Twenty-two of the owner's interests are
about a place, so twenty-two of them said *rests on one reading* when
they rest on two, and the second date was gone.

So a place is an **entity** -- a thing several readings are about --
and each visit is an **observation** with its own day, pointing
`about` at it. The interest points `about` at the place as well,
which is what makes *which places do I go to for this* a walk rather
than a query somebody has to write (#391).

## A label is written here, never copied

Asked for as a declaration, and it is a stronger answer than a
declaration: **no label in this graph contains anything the owner
wrote, said, or photographed.** Every one is a sentence this file
composes from a *kind* -- *a note the library read* -- or a topic
word that the interest derivation already published, or an opaque
place name.

Nothing here reads a caption's text, a note's body, a page's title
or a file's path. A consumer may therefore show a label without
asking what privacy level produced it, which is the property a
screen actually needs. It is checked rather than promised: a test
puts the owner's own words in every field the builder touches and
fails if any of them reaches a node.

## Rebuilding is not duplicating

Every id is derived from what the node is rather than from when it was
made, so building twice writes the same ids and the store updates them.
A graph that grew a second copy of everything on each `refresh` would
be useless within a week.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from kiseki.application.sourcing import is_reference, source_of
from kiseki.domain.evidence.graph import (
    Edge,
    EvidenceGraph,
    Node,
    NodeKind,
    graph_of,
)
from kiseki.domain.insight import Insight, InsightReport
from kiseki.domain.interests import Profile

ALGORITHM_VERSION = "1"
"""Which set of rules built a graph, carried in the document.

So that a consumer can tell two kinds of change apart. A finding
that appeared because the owner did something new, and one that
appeared because this file learned to look somewhere else, are
different news; a screen that showed them alike would report a
refactor as a life event.

Bumped when what is built from the same readings changes."""

PLACE_PREFIX = "place:"

INTEREST_ID = "interest:{topic}"
VISIT_ID = "visit:{place}:{day}"
CONCLUSION_ID = "insight:{topic}:{kind}"
PLACE_ID = "place-{rank}"


@dataclass(frozen=True)
class _Places:
    """Opaque names for places, so no coordinate becomes an id.

    Ranked by how often each was cited, which is stable across a
    rebuild as long as the evidence is, and is the same ordering
    grounding uses when it says *Place 1*.
    """

    by_reference: dict[str, str]

    @classmethod
    def over(cls, references: Sequence[str]) -> _Places:
        counted: dict[str, int] = {}
        for reference in references:
            if reference.startswith(PLACE_PREFIX):
                counted[reference] = counted.get(reference, 0) + 1
        ranked = sorted(counted, key=lambda reference: (-counted[reference], reference))
        return cls(
            {reference: PLACE_ID.format(rank=rank) for rank, reference in enumerate(ranked, 1)}
        )

    def name(self, reference: str) -> str | None:
        return self.by_reference.get(reference)


def _what_a_finding_rests_on(finding: Insight) -> tuple[str, ...]:
    """The readings under an insight, including the dormant case.

    Twelve of the owner's six hundred insights cite no evidence at
    all, and every one of them is `dormant` -- which is a finding
    about an **absence**, so there is nothing recent to point at.
    They are not conclusions resting on nothing, and the graph was
    right to refuse them: `derived_from` already names the kept
    reading they were computed over.

    So the readings are the evidence plus whatever in `derived_from`
    is a reference. The rest of `derived_from` is command names --
    `trend`, `lifecycle` -- and citing those as evidence would be
    citing the name of a derivation as support for itself."""
    named = list(finding.evidence)
    named += [item for item in finding.derived_from if is_reference(item)]
    seen: dict[str, None] = {}
    for item in named:
        seen.setdefault(item)
    return tuple(seen)


def build_graph(profile: Profile | None, insights: InsightReport | None) -> EvidenceGraph:
    """The graph of what this library currently believes, and why.

    Whole, so the rule that every conclusion reaches an observation is
    checked here rather than trusted -- a conclusion assembled without
    one is a bug in this file and should not reach storage.
    """
    interests = tuple(profile.interests) if profile is not None else ()
    findings = tuple(insights.insights) if insights is not None else ()

    # A topic can itself be a place -- `place:34.7,135.4` is a perfectly
    # ordinary interest in this library -- so topics are named here
    # alongside references. The first build against the owner's real
    # library found this; every synthetic test had topics like
    # 'camping', which is what synthetic data is for and what it costs.
    named = [evidence.reference for interest in interests for evidence in interest.evidence]
    named += [reference for finding in findings for reference in finding.evidence]
    named += [
        reference
        for finding in findings
        for reference in finding.derived_from
        if is_reference(reference)
    ]
    named += [interest.topic for interest in interests]
    named += [finding.topic for finding in findings]
    places = _Places.over(named)

    nodes: dict[str, Node] = {}
    edges: list[Edge] = []
    # The days at each place, so a finding that cites the place can rest
    # on the readings rather than on the thing.
    visits_to: dict[str, list[str]] = {}

    def entity(reference: str) -> str:
        """The place a reading is about, named and never located."""
        node_id = places.name(reference) or reference
        if node_id not in nodes:
            nodes[node_id] = Node(
                id=node_id,
                kind=NodeKind.ENTITY,
                label=f"{node_id}, returned to",
            )
        return node_id

    def observe(reference: str, when: datetime | None = None) -> str:
        """One reading. A visit is keyed by its day, because a place
        cited twice is two visits and collapsing them loses one."""
        source = source_of(reference)
        if reference.startswith(PLACE_PREFIX):
            place = entity(reference)
            if when is None:
                # Unreachable today, and an error rather than a
                # silent invention: a finding cites the place and is
                # handled below, so the only caller that gets here
                # has a date. Minting `visit:place-1:undated` would
                # claim a visit whose day we happen not to know,
                # which is more than the evidence says.
                raise ValueError(
                    f"{reference} arrived with no day; a place without one is a "
                    "thing rather than a reading of it"
                )
            day = f"{when:%Y-%m-%d}"
            node_id = VISIT_ID.format(place=place, day=day)
            if node_id not in nodes:
                nodes[node_id] = Node(
                    id=node_id,
                    kind=NodeKind.OBSERVATION,
                    label=f"a day at {place}",
                    source=source.name.lower(),
                    occurred_at=when,
                )
                visits_to.setdefault(place, []).append(node_id)
                edges.append(
                    Edge(
                        id=f"{node_id}|about|{place}",
                        source=node_id,
                        target=place,
                        kind="about",
                    )
                )
            return node_id
        if reference not in nodes:
            nodes[reference] = Node(
                id=reference,
                kind=NodeKind.OBSERVATION,
                label=f"a {source.label} the library read",
                source=source.name.lower(),
                occurred_at=when,
            )
        return reference

    for interest in interests:
        topic = places.name(interest.topic) or interest.topic
        interest_id = INTEREST_ID.format(topic=topic)
        nodes[interest_id] = Node(
            id=interest_id,
            kind=NodeKind.INTEREST,
            label=topic,
            confidence=interest.confidence,
        )
        if interest.topic.startswith(PLACE_PREFIX):
            place = entity(interest.topic)
            edges.append(
                Edge(
                    id=f"{interest_id}|about|{place}",
                    source=interest_id,
                    target=place,
                    kind="about",
                )
            )
        for evidence in interest.evidence:
            target = observe(evidence.reference, evidence.observed_at)
            edges.append(
                Edge(
                    id=f"{interest_id}|rests_on|{target}",
                    source=interest_id,
                    target=target,
                    kind="rests_on",
                )
            )

    for finding in findings:
        topic = places.name(finding.topic) or finding.topic
        conclusion_id = CONCLUSION_ID.format(topic=topic, kind=finding.kind.value)
        nodes[conclusion_id] = Node(
            id=conclusion_id,
            kind=NodeKind.CONCLUSION,
            label=f"{topic} is {finding.direction.value}",
            confidence=finding.confidence,
        )
        for reference in _what_a_finding_rests_on(finding):
            if reference.startswith(PLACE_PREFIX):
                # A finding cites the place; what it rests on are the
                # visits to it, which the interests above already made.
                # Pointing at the place itself would have the finding
                # rest on a thing rather than on a reading.
                place = entity(reference)
                for visit in visits_to.get(place, ()):
                    edges.append(
                        Edge(
                            id=f"{conclusion_id}|derived_from|{visit}",
                            source=conclusion_id,
                            target=visit,
                            kind="derived_from",
                            because=tuple(finding.derived_from),
                        )
                    )
                continue
            target = observe(reference)
            edges.append(
                Edge(
                    id=f"{conclusion_id}|derived_from|{target}",
                    source=conclusion_id,
                    target=target,
                    kind="derived_from",
                    because=tuple(finding.derived_from),
                )
            )

    return graph_of(nodes.values(), edges, built_by=ALGORITHM_VERSION)
