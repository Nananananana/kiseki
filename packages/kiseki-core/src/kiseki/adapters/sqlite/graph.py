"""The evidence graph in SQLite, which is the database already open.

No new dependency and no second store. A graph database would be a
better fit for traversal and a worse fit for everything else here: one
owner, one file, one process, and a library whose whole promise is that
nothing leaves the machine. SQLite walks a few thousand edges faster
than a person can read the answer.

## The shape, and why it is this shape

Two tables and a join, rather than one table of JSON blobs.

    graph_nodes           id, kind, label, source, occurred_at,
                          confidence, importance, metadata, visual
    graph_edges           id, source_id, target_id, kind, strength,
                          confidence, because, metadata, visual
    graph_edge_evidence   edge_id, node_id

**Typed columns for what every node has; JSON for what only some
carry.** `metadata` and `visual` are the extension point, and the rule
that keeps them from becoming a schema is written here rather than
remembered: **anything a query filters on graduates to a column.** A
JSON bag is a reasonable place to put a field nobody searches and a
poor index for one that everybody does.

**An edge's evidence is a table, not a list in a column**, by that same
rule -- *which edges cite this observation* is a question worth asking,
and a foreign key answers it while also making the domain's check
(every cited id is a node the graph holds) true in the database rather
than merely checked in Python.

**`UNIQUE (source_id, target_id, kind)` makes one claim stored twice
impossible** rather than merely discouraged, which is the same rule
`graph_of` applies in memory. Two places enforcing one rule is
acceptable when the second cannot be bypassed; two places *deciding*
one rule would not be.

**The index on `target_id`** is the backwards walk, which is the read
this whole structure exists for.

## Writing is additive

`save` replaces the nodes and edges it is given and touches nothing
else, so a producer that knows about photographs writes what it knows
without deleting what the recorder wrote. Removing is `forget`, which
is separate because it is the one that loses something.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from kiseki.domain.evidence.graph import (
    Edge,
    EvidenceGraph,
    Node,
    NodeKind,
    graph_of,
    part_of,
)
from kiseki.domain.evidence.visual import EdgeVisual, NodeVisual

GRAPH_TABLES = """
CREATE TABLE IF NOT EXISTS graph_nodes (
    id          TEXT PRIMARY KEY,
    kind        TEXT NOT NULL,
    label       TEXT NOT NULL,
    source      TEXT,
    occurred_at TEXT,
    confidence  REAL,
    importance  REAL,
    metadata    TEXT NOT NULL DEFAULT '{}',
    visual      TEXT
);

CREATE INDEX IF NOT EXISTS graph_nodes_kind ON graph_nodes(kind);
CREATE INDEX IF NOT EXISTS graph_nodes_source ON graph_nodes(source);
CREATE INDEX IF NOT EXISTS graph_nodes_occurred_at ON graph_nodes(occurred_at);

CREATE TABLE IF NOT EXISTS graph_edges (
    id          TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_id   TEXT NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    strength    REAL,
    confidence  REAL,
    because     TEXT NOT NULL DEFAULT '[]',
    metadata    TEXT NOT NULL DEFAULT '{}',
    visual      TEXT,
    UNIQUE (source_id, target_id, kind)
);

CREATE INDEX IF NOT EXISTS graph_edges_source ON graph_edges(source_id);
CREATE INDEX IF NOT EXISTS graph_edges_target ON graph_edges(target_id);
CREATE INDEX IF NOT EXISTS graph_edges_kind ON graph_edges(kind);

CREATE TABLE IF NOT EXISTS graph_edge_evidence (
    edge_id TEXT NOT NULL REFERENCES graph_edges(id) ON DELETE CASCADE,
    node_id TEXT NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    PRIMARY KEY (edge_id, node_id)
);

CREATE INDEX IF NOT EXISTS graph_edge_evidence_node ON graph_edge_evidence(node_id);
"""


def _as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _node_visual(text: str | None) -> NodeVisual | None:
    if not text:
        return None
    return NodeVisual(**json.loads(text))


def _edge_visual(text: str | None) -> EdgeVisual | None:
    if not text:
        return None
    return EdgeVisual(**json.loads(text))


def _visual_json(visual: NodeVisual | EdgeVisual | None) -> str | None:
    if visual is None:
        return None
    return _as_json(vars(visual))


class SqliteEvidenceGraph:
    """The graph, in the database the rest of the library already opened."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """The tables are the schema's, created and migrated by
        `connect` like every other table here (ADR-0018). A
        repository that made its own would let a database gain them
        without the version saying so."""
        self._connection = connection

    # ---------------------------------------------------------------- write

    def save(self, graph: EvidenceGraph) -> int:
        """Store these nodes and edges, replacing what each said before.

        One transaction, and the nodes first: an edge references its
        ends, so writing edges before their nodes would be refused by
        the foreign keys the connection turns on.
        """
        written = 0
        with self._connection:
            for node in graph.nodes:
                self._connection.execute(
                    """
                    INSERT INTO graph_nodes
                        (id, kind, label, source, occurred_at,
                         confidence, importance, metadata, visual)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        kind = excluded.kind,
                        label = excluded.label,
                        source = excluded.source,
                        occurred_at = excluded.occurred_at,
                        confidence = excluded.confidence,
                        importance = excluded.importance,
                        metadata = excluded.metadata,
                        visual = excluded.visual
                    """,
                    (
                        node.id,
                        node.kind.value,
                        node.label,
                        node.source,
                        node.occurred_at.isoformat() if node.occurred_at else None,
                        node.confidence,
                        node.importance,
                        _as_json(node.metadata),
                        _visual_json(node.visual),
                    ),
                )
                written += 1
            for edge in graph.edges:
                self._connection.execute(
                    """
                    INSERT INTO graph_edges
                        (id, source_id, target_id, kind, strength,
                         confidence, because, metadata, visual)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        source_id = excluded.source_id,
                        target_id = excluded.target_id,
                        kind = excluded.kind,
                        strength = excluded.strength,
                        confidence = excluded.confidence,
                        because = excluded.because,
                        metadata = excluded.metadata,
                        visual = excluded.visual
                    """,
                    (
                        edge.id,
                        edge.source,
                        edge.target,
                        edge.kind,
                        edge.strength,
                        edge.confidence,
                        _as_json(list(edge.because)),
                        _as_json(edge.metadata),
                        _visual_json(edge.visual),
                    ),
                )
                self._connection.execute(
                    "DELETE FROM graph_edge_evidence WHERE edge_id = ?", (edge.id,)
                )
                for cited in edge.evidence:
                    self._connection.execute(
                        "INSERT INTO graph_edge_evidence (edge_id, node_id) VALUES (?, ?)",
                        (edge.id, cited),
                    )
                written += 1
        return written

    def forget(self, node_ids: Sequence[str]) -> int:
        """Remove these nodes; the edges follow them by cascade."""
        if not node_ids:
            return 0
        marks = ",".join("?" for _ in node_ids)
        with self._connection:
            cursor = self._connection.execute(
                f"DELETE FROM graph_nodes WHERE id IN ({marks})",
                tuple(node_ids),
            )
        return int(cursor.rowcount)

    # ----------------------------------------------------------------- read

    def all(self) -> EvidenceGraph:
        """Everything. Convenient, and the read that stops being
        reasonable first -- see `around`."""
        nodes = self._nodes_where("1 = 1", ())
        return graph_of(nodes.values(), self._edges_among(set(nodes)))

    def around(self, node_id: str, steps: int = 1) -> EvidenceGraph:
        """The neighbourhood of one node, out to `steps` edges.

        Breadth first, following edges in both directions, because a
        reader asking about a conclusion wants what it rests on and a
        reader asking about an observation wants what was concluded
        from it. Comes back marked as a piece.
        """
        if steps < 0:
            raise ValueError("a neighbourhood cannot be a negative number of steps across")
        reached = {node_id}
        edge = {node_id}
        for _ in range(steps):
            if not edge:
                break
            neighbours = self._neighbour_ids(edge)
            edge = neighbours - reached
            reached |= neighbours
        nodes = self._nodes_where(
            f"id IN ({','.join('?' for _ in reached)})", tuple(sorted(reached))
        )
        return part_of(nodes.values(), self._edges_among(set(nodes)))

    def of_kind(self, kind: NodeKind) -> tuple[Node, ...]:
        found = self._nodes_where("kind = ?", (kind.value,))
        return tuple(found[key] for key in sorted(found))

    def count(self) -> tuple[int, int]:
        nodes = self._connection.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
        edges = self._connection.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
        return int(nodes), int(edges)

    # -------------------------------------------------------------- private

    def _neighbour_ids(self, ids: set[str]) -> set[str]:
        marks = ",".join("?" for _ in ids)
        rows = self._connection.execute(
            f"""
            SELECT source_id, target_id FROM graph_edges
            WHERE source_id IN ({marks}) OR target_id IN ({marks})
            """,
            tuple(sorted(ids)) * 2,
        ).fetchall()
        return {end for row in rows for end in row}

    def _nodes_where(self, clause: str, values: tuple[Any, ...]) -> dict[str, Node]:
        rows = self._connection.execute(
            f"""
            SELECT id, kind, label, source, occurred_at, confidence, importance, metadata, visual
            FROM graph_nodes WHERE {clause}
            """,
            values,
        ).fetchall()
        return {row[0]: _to_node(row) for row in rows}

    def _edges_among(self, ids: set[str]) -> list[Edge]:
        if not ids:
            return []
        marks = ",".join("?" for _ in ids)
        rows = self._connection.execute(
            f"""
            SELECT id, source_id, target_id, kind, strength, confidence,
                   because, metadata, visual
            FROM graph_edges
            WHERE source_id IN ({marks}) AND target_id IN ({marks})
            ORDER BY id
            """,
            tuple(sorted(ids)) * 2,
        ).fetchall()
        cited = self._evidence_for({row[0] for row in rows})
        return [_to_edge(row, tuple(cited.get(row[0], ()))) for row in rows]

    def _evidence_for(self, edge_ids: set[str]) -> dict[str, list[str]]:
        if not edge_ids:
            return {}
        marks = ",".join("?" for _ in edge_ids)
        rows = self._connection.execute(
            f"""
            SELECT edge_id, node_id FROM graph_edge_evidence
            WHERE edge_id IN ({marks}) ORDER BY edge_id, node_id
            """,
            tuple(sorted(edge_ids)),
        ).fetchall()
        found: dict[str, list[str]] = {}
        for edge_id, node_id in rows:
            found.setdefault(edge_id, []).append(node_id)
        return found


def _to_node(row: Iterable[Any]) -> Node:
    (
        node_id,
        kind,
        label,
        source,
        occurred_at,
        confidence,
        importance,
        metadata,
        visual,
    ) = row
    return Node(
        id=node_id,
        kind=NodeKind(kind),
        label=label,
        source=source,
        occurred_at=datetime.fromisoformat(occurred_at) if occurred_at else None,
        confidence=confidence,
        importance=importance,
        metadata=json.loads(metadata),
        visual=_node_visual(visual),
    )


def _to_edge(row: Iterable[Any], evidence: tuple[str, ...]) -> Edge:
    edge_id, source_id, target_id, kind, strength, confidence, because, metadata, visual = row
    return Edge(
        id=edge_id,
        source=source_id,
        target=target_id,
        kind=kind,
        strength=strength,
        confidence=confidence,
        evidence=evidence,
        because=tuple(json.loads(because)),
        metadata=json.loads(metadata),
        visual=_edge_visual(visual),
    )
