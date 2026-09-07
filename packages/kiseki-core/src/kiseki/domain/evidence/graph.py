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

## Three kinds of thing, and the direction between them

    fact         a stored reading; immutable, and the only kind that is
    interest     a derivation resting on facts
    conclusion   a finding resting on interests and facts
    entity       what several of the above are about

The arrows point at what came first, always. `conclusion -> interest ->
fact` reads *because of*, and walking it backwards is the whole point.
Nothing points forward, because a fact does not know what will later be
derived from it, and an edge that claimed otherwise would have to be
rewritten when the next derivation ran -- which would make facts
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
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique


@unique
class NodeKind(Enum):
    """What a node is, which decides what may point at it."""

    FACT = "fact"
    """A stored reading. The only kind that is immutable, and the only
    kind a walk backwards can end on."""

    ENTITY = "entity"
    """A place, a topic, a thing several observations are about."""

    INTEREST = "interest"
    CONCLUSION = "conclusion"


@unique
class EdgeKind(Enum):
    """A closed set, and small on purpose.

    The requirements list a dozen relationship types. Ten of them
    describe things this library does not yet derive, and a type that
    nothing produces is a promise rather than a relationship. These
    three are the ones the existing derivations already mean.
    """

    RESTS_ON = "rests_on"
    """An interest to the reading under it."""

    DERIVED_FROM = "derived_from"
    """A conclusion to what produced it."""

    ABOUT = "about"
    """Anything to the entity it concerns."""


_A_COORDINATE = re.compile(r"-?\d{1,3}\.\d+\s*,\s*-?\d{1,3}\.\d+")
"""A latitude and a longitude, however they are spelled. Blurring is
not enough here: two decimals still names a kilometre square, and a
graph is read by whoever holds it rather than by the owner."""


@dataclass(frozen=True)
class Node:
    """One thing the graph knows about."""

    id: str
    kind: NodeKind
    label: str
    """What to call it in a sentence. Never where it is."""

    occurred_at: datetime | None = None
    """When, where the node is about a moment. `None` for an entity or
    a derivation, which are about a pattern rather than an instant."""

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


@dataclass(frozen=True)
class Edge:
    """One relationship, pointing at what came first."""

    source: str
    target: str
    kind: EdgeKind

    def __post_init__(self) -> None:
        if self.source == self.target:
            raise ValueError("a thing cannot be derived from itself")


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
            if node.kind is NodeKind.CONCLUSION and not self._facts_under(node.id, seen):
                raise ValueError(
                    f"the conclusion {node.id!r} reaches no fact; a conclusion resting on "
                    "nothing observed is not a weak one, it is one this library could not "
                    "have produced"
                )

    def _outgoing(self) -> dict[str, list[Edge]]:
        outgoing: dict[str, list[Edge]] = defaultdict(list)
        for edge in self.edges:
            outgoing[edge.source].append(edge)
        return outgoing

    def _facts_under(self, node_id: str, by_id: dict[str, Node]) -> tuple[Node, ...]:
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
            if node is not None and node.kind is NodeKind.FACT and current != node_id:
                found[current] = node
            pending.extend(edge.target for edge in outgoing[current])
        return tuple(found[key] for key in sorted(found))

    def facts_under(self, node_id: str) -> tuple[Node, ...]:
        """What this rests on, in the end: the readings, and nothing else.

        The backwards walk the whole structure exists for. A reader who
        doubts a conclusion is handed the observations under it rather
        than a score.
        """
        by_id = {node.id: node for node in self.nodes}
        if node_id not in by_id:
            raise KeyError(f"{node_id!r} is not in this graph")
        return self._facts_under(node_id, by_id)

    def neighbours(self, node_id: str) -> tuple[Edge, ...]:
        """Every edge with this node at either end, in a fixed order."""
        touching = [edge for edge in self.edges if node_id in (edge.source, edge.target)]
        return tuple(sorted(touching, key=lambda edge: (edge.kind.value, edge.source, edge.target)))

    def of_kind(self, kind: NodeKind) -> tuple[Node, ...]:
        return tuple(node for node in self.nodes if node.kind is kind)

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
        kept[(edge.source, edge.target, edge.kind.value)] = edge
    return EvidenceGraph(
        nodes=tuple(nodes),
        edges=tuple(kept[key] for key in sorted(kept)),
    )
