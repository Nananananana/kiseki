"""Why the library concluded something, as a thing a program can walk.

The library has always kept provenance. An `Insight` refuses to exist
without naming what it was derived from, an `Interest` carries the
evidence under it, and nothing here is ever inferred from a model's
recollection. What it could not do is **show its working**: the
provenance is a tuple of strings inside a row, which a person can read
and a program cannot traverse.

So a reader could be told *nature is rising in your library, on eleven
sightings* and had no way to ask which eleven, or what those rested on
in turn. This is that question made answerable mechanically.

## Roles are closed; sources are open

Two vocabularies, and the difference between them is the whole
design.

    kind      what a node is to the reasoning     observation, event,
                                                  entity, interest,
                                                  conclusion
    source    what in the world it came from      photograph, note,
                                                  page, audio, ...

**A kind is a role, and roles do not grow when a source arrives.** A
recording and a photograph are both observations; what changes is
what the observation came from, not what it is to the argument above
it.

**A source is a fact about the world, so it may not be a closed
set.** This library learned that expensively. `EvidenceSource` was an
enum, the web shipped in v0.11, and `source_of` fell through to its
photograph default for two releases -- so an answer resting entirely
on what the owner wrote and read reported *read from photograph*, and
`EvidenceSource.NOTE` existed the whole time with nothing able to
return it. A closed vocabulary did not prevent an unknown source. It
made an unknown source indistinguishable from a camera.

So a source here is any name, checked for shape and never for
membership. A recorder producing something this library has never
heard of gets a node that says what it is, rather than one that
quietly claims to be a photograph. That is ADR-0063's rule -- any
source may be absent, a derivation names what it read -- extended to
sources that do not exist yet, and it is what lets a source be added
by writing a producer rather than by editing this file.

## An observation is not an event

A photograph taken at the park, a recording made there and a line
written that evening are three readings of one afternoon. A model
that cannot say so either counts the afternoon three times or throws
two of the readings away, and both are wrong in a way that grows with
the number of sources.

So an event is its own kind, and several observations may point at
one. The fusing that decides *which* observations belong to one event
is not here -- it is a derivation, and it needs the thresholds this
phase deliberately has none of. What is here is the shape that lets
it be written without changing anything else.

An event carries no `source` of its own. What it came from is the set
of observations under it, which is structure rather than a field and
so cannot fall out of step with the edges.

## Anything may point at anything

No edge is restricted by the kinds at its ends. A fact may point at a
fact, an interest at another interest, an entity at anything. The
library's own derivations use a handful of the types below and the rest
are declared for producers that will come, because a graph whose shape
is decided by today's derivations would have to be migrated by every
one that follows.

The arrows point at what came first, always. `conclusion ->
interest -> fact` reads *because of*, and walking it backwards is the
point. Nothing points forward, because a fact does not know what will
later be derived from it, and an edge that claimed otherwise would have
to be rewritten when the next derivation ran -- which would make facts
mutable through the back door.

## The invariant

**Every conclusion reaches a fact.** A conclusion that does not is not a
weak conclusion; it is one that rests on nothing observed, and this
library has no way to have produced it. So the graph refuses to hold
one rather than storing it and hoping a reader checks.

That is the same shape as `Insight.__post_init__` refusing an insight
that cannot name what it was derived from, raised from one object to
the structure between them.

## No coordinates, anywhere in it

A graph is a document written for another program -- this is exactly
the shape of thing that wrote the owner's doorstep at full precision
when a default failed open (ADR-0095). And a place is the most
sensitive node here by a distance.

So a node's label may not contain a coordinate at all, and
`__post_init__` refuses one. A place is identified the way grounding
already identifies it (ADR-0040): by an opaque name, with its cadence
and its shares carried as the derivation's own words, never by where it
is. The rule is here rather than at the serving boundary because a
boundary can be bypassed by a second caller and a constructor cannot.

## What is deliberately not here

No hypotheses, no confidence on an edge, no decay. The requirements
this comes from ask for all three, and each needs a number this library
cannot yet produce honestly: the per-kind confidences are not
comparable (#390), so a strength summed from them would give the
incomparability a decimal point. Phase 1 stores what is known and
counts it. See `docs/proposals/0010`.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, unique
from typing import Any


@unique
class NodeKind(Enum):
    """What a node is to the reasoning. Closed, because these are roles.

    A recording, a photograph and a page are all observations. What
    differs between them is the source, which is a separate and open
    field -- growing this enum every time a recorder arrives is what
    makes a model brittle."""

    OBSERVATION = "observation"
    """One stored reading, from one source. Immutable, and the
    only kind a walk backwards can end on."""

    EVENT = "event"
    """Something that happened, which several observations may
    each be witness to.

    Separate from the observation on purpose. A photograph at the
    park, a recording made there and a line written that evening are
    three readings of one afternoon, and a model that cannot say so
    either counts the afternoon three times or throws two of the
    readings away.

    An event carries no `source` of its own: what it came from is the
    set of observations under it, which is structure rather than a
    field, and cannot fall out of step with the edges."""

    ENTITY = "entity"
    """A place, a person, a topic -- a thing several
    observations are about."""

    INTEREST = "interest"
    CONCLUSION = "conclusion"


EDGE_KINDS: tuple[str, ...] = (
    "rests_on",
    "derived_from",
    "about",
    "related_to",
    "similar_to",
    "precedes",
    "follows",
    "supports",
    "contradicts",
    "reinforces",
    "weakens",
    "influences",
    "belongs_to",
    "supersedes",
)
"""Every relationship a producer may declare.

Declared rather than closed. The library's own derivations use the
first three; the rest are named for the producers and the phases
that follow, so adding one is a line here rather than a migration.

`causes` is the one name from the proposals that is deliberately
absent. Correlation is not causation, and A happening before B is
`precedes` -- a causal claim is something that can be argued with,
which makes it a hypothesis rather than an edge."""


_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_A_COORDINATE = re.compile(r"-?\d{1,3}\.\d+\s*,\s*-?\d{1,3}\.\d+")
"""A latitude and a longitude, however they are spelled. Blurring is
not enough here: two decimals still names a kilometre square, and a
graph is read by whoever holds it rather than by the owner."""


@dataclass(frozen=True)
class Node:
    """One thing the graph knows about, from wherever it came."""

    id: str
    kind: NodeKind
    label: str
    """What to call it in a sentence. Never where it is."""

    source: str | None = None
    """What in the world this came from -- `photograph`, `note`,
    `page`, `audio`, whatever a producer calls its own output.

    Checked for shape and never for membership, so a recorder this
    library has never heard of produces a node that says what it is
    rather than one that quietly claims to be a photograph. Required on
    a fact, which is the only kind that comes from anywhere; `None` on
    a derivation, which comes from the facts under it.
    """

    occurred_at: datetime | None = None
    """When, where the node is about a moment. `None` for an entity or
    a derivation, which are about a pattern rather than an instant."""

    attributes: dict[str, Any] = field(default_factory=dict)
    """What only this kind of node has, for a producer that knows more
    than the shape above.

    The extension point, and the smallest one that works: a field here
    costs no migration, and anything a query needs to filter on should
    graduate to a column of its own rather than living in here forever.
    """

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("a node without an id cannot be pointed at")
        if not self.label.strip():
            raise ValueError("a node that cannot be named cannot be shown to anybody")
        if _A_COORDINATE.search(self.label):
            raise ValueError(
                "a graph node may not carry a coordinate; a place is named the way "
                "grounding names one, by its cadence and never by where it is (ADR-0040)"
            )
        if self.kind is NodeKind.OBSERVATION and not self.source:
            raise ValueError(
                f"the observation {self.id!r} does not say what it came from; an unnamed source "
                "is indistinguishable from a photograph, which is how the web went two "
                "releases misreported"
            )
        if self.source is not None and not _NAME.match(self.source):
            raise ValueError(
                f"{self.source!r} is not the shape of a source name; lower case, "
                "digits and underscores, so a vocabulary stays a vocabulary"
            )


@dataclass(frozen=True)
class Edge:
    """One relationship, pointing at what came first."""

    source: str
    target: str
    kind: str

    attributes: dict[str, Any] = field(default_factory=dict)
    """As on a node, and for the same reason. No confidence here yet:
    see the module docstring."""

    def __post_init__(self) -> None:
        if self.source == self.target:
            raise ValueError("a thing cannot be derived from itself")
        if self.kind not in EDGE_KINDS:
            raise ValueError(
                f"{self.kind!r} is not a declared relationship; add it to EDGE_KINDS, "
                "which is one line, so that every type in the graph can be listed"
            )


@dataclass(frozen=True)
class EvidenceGraph:
    """Everything the library knows about why it concluded what it did."""

    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()

    def __post_init__(self) -> None:
        seen: dict[str, Node] = {}
        for node in self.nodes:
            if node.id in seen:
                raise ValueError(f"two nodes share the id {node.id!r}")
            seen[node.id] = node
        for edge in self.edges:
            for end in (edge.source, edge.target):
                if end not in seen:
                    raise ValueError(f"an edge points at {end!r}, which is not in the graph")
        for node in self.nodes:
            if node.kind is NodeKind.CONCLUSION and not self._observations_under(node.id, seen):
                raise ValueError(
                    f"the conclusion {node.id!r} reaches no observation; a conclusion resting on "
                    "nothing observed is not a weak one, it is one this library could not "
                    "have produced"
                )

    def _outgoing(self) -> dict[str, list[Edge]]:
        outgoing: dict[str, list[Edge]] = defaultdict(list)
        for edge in self.edges:
            outgoing[edge.source].append(edge)
        return outgoing

    def _observations_under(self, node_id: str, by_id: dict[str, Node]) -> tuple[Node, ...]:
        """Every fact reachable from here, following the arrows.

        Cycle-safe, because a graph assembled from several derivations
        is not guaranteed acyclic by anything and a traversal that
        assumed it would hang rather than fail.
        """
        outgoing = self._outgoing()
        found: dict[str, Node] = {}
        walked: set[str] = set()
        pending = [node_id]
        while pending:
            current = pending.pop()
            if current in walked:
                continue
            walked.add(current)
            node = by_id.get(current)
            if node is not None and node.kind is NodeKind.OBSERVATION and current != node_id:
                found[current] = node
            pending.extend(edge.target for edge in outgoing[current])
        return tuple(found[key] for key in sorted(found))

    def observations_under(self, node_id: str) -> tuple[Node, ...]:
        """What this rests on, in the end: the observations, and nothing else.

        The backwards walk the whole structure exists for. A reader who
        doubts a conclusion is handed the observations under it rather
        than a score.
        """
        by_id = {node.id: node for node in self.nodes}
        if node_id not in by_id:
            raise KeyError(f"{node_id!r} is not in this graph")
        return self._observations_under(node_id, by_id)

    def sources_under(self, node_id: str) -> tuple[str, ...]:
        """Which kinds of witness a conclusion actually rests on.

        The question a reader asks before deciding whether to believe
        it, and the one that was answered wrongly for two releases when
        an unrecognised source fell through to `photograph`.
        """
        found = {node.source for node in self.observations_under(node_id) if node.source}
        return tuple(sorted(found))

    def neighbours(self, node_id: str) -> tuple[Edge, ...]:
        """Every edge with this node at either end, in a fixed order."""
        touching = [edge for edge in self.edges if node_id in (edge.source, edge.target)]
        return tuple(sorted(touching, key=lambda edge: (edge.kind, edge.source, edge.target)))

    def of_kind(self, kind: NodeKind) -> tuple[Node, ...]:
        return tuple(node for node in self.nodes if node.kind is kind)

    def of_source(self, source: str) -> tuple[Node, ...]:
        """Every node from one kind of witness, whatever the library
        knows about that kind -- which may be nothing at all."""
        return tuple(node for node in self.nodes if node.source == source)

    @property
    def sources(self) -> tuple[str, ...]:
        """Every source present, in a fixed order. Not a fixed list: a
        library holds what it was given."""
        return tuple(sorted({node.source for node in self.nodes if node.source}))

    @property
    def empty(self) -> bool:
        """A library with nothing derived yet, which is its own answer."""
        return not self.nodes


def graph_of(nodes: Iterable[Node], edges: Sequence[Edge]) -> EvidenceGraph:
    """Assemble a graph, dropping duplicate edges rather than storing two.

    Two derivations naming the same evidence is normal and says nothing
    extra; the second copy would only make a count wrong later.
    """
    kept: dict[tuple[str, str, str], Edge] = {}
    for edge in edges:
        kept[(edge.source, edge.target, edge.kind)] = edge
    return EvidenceGraph(
        nodes=tuple(nodes),
        edges=tuple(kept[key] for key in sorted(kept)),
    )
