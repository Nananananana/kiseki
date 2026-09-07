"""Where the evidence graph is kept, as the core is willing to ask for it.

Four questions, and the third is the one that decides whether this
scales. The whole graph is the easy read and the one that stops working
first: the requirements this comes from target tens of thousands of
events, and a command that loads all of them to answer *why did you
conclude that* has done the wrong amount of work by two orders of
magnitude.

So `around` is the primitive and `all` is the convenience, rather than
the other way round. A neighbourhood comes back marked as a piece
rather than the whole, because a conclusion three steps from its
observations still rests on them in storage and a view that cannot see
them must not be read as one that says it rests on nothing.

The implementer never imports this; the port belongs to the core
(ADR-0004).
"""

from collections.abc import Sequence
from typing import Protocol

from kiseki.domain.evidence.graph import EvidenceGraph, Node, NodeKind


class EvidenceGraphRepository(Protocol):
    """The graph, kept between runs."""

    def save(self, graph: EvidenceGraph) -> int:
        """Store this graph, replacing what each node and edge said
        before. Returns how many nodes and edges were written.

        Additive rather than a replacement of everything: a producer
        that knows about photographs writes what it knows without
        deleting what the recorder wrote. Removing is `forget`, which
        is a separate act because it is the one that loses something.
        """
        ...

    def all(self) -> EvidenceGraph:
        """Everything, as a whole graph. Convenient, and the read that
        stops being reasonable first."""
        ...

    def around(self, node_id: str, steps: int = 1) -> EvidenceGraph:
        """The neighbourhood of one node, out to `steps` edges.

        Marked as a piece rather than the whole, so nothing mistakes a
        conclusion whose observations lie outside the view for one that
        rests on nothing.
        """
        ...

    def of_kind(self, kind: NodeKind) -> tuple[Node, ...]:
        """Every node of one role, without walking anything."""
        ...

    def forget(self, node_ids: Sequence[str]) -> int:
        """Remove these nodes and every edge touching them; how many went.

        Named for what it costs. An observation removed here is a
        reading the graph can no longer reach, and a conclusion that
        rested on it will fail the check the next time the graph is
        assembled whole -- which is the intended behaviour, not a
        problem to be worked around.
        """
        ...

    def count(self) -> tuple[int, int]:
        """How many nodes and how many edges, without reading either."""
        ...
