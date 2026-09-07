"""What a drawing of the graph may want, kept away from the reasoning.

One graph model, two readers. The orchestrator will draw this, and a
drawing wants things the analysis has no use for -- a group to colour
by, a size to scale by, a shorter label than the sentence a derivation
wrote. Deriving a second model for the picture would mean keeping two
in step, and they would drift on the first change to either.

So the hints live here, on the node and the edge, and **nothing in the
reasoning reads them**. That is the whole rule, and it is checkable:
a test greps the graph module for the field and fails if the analysis
has started depending on how something looks.

## What is deliberately not here

No positions and no colours. A position computed here would be a layout
decided by the library and imposed on every viewer, and a colour is a
palette decision belonging to whoever draws. What a viewer needs from
us is what things *are* -- which group, which weight, what to call it
in a small box -- and the drawing is theirs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NodeVisual:
    """Hints for drawing one node. Never read by a derivation."""

    short_label: str | None = None
    """A few words, where the node's own label is a sentence. `None`
    means the label will do."""

    group: str | None = None
    """What to draw alike. A source, a topic, a period -- whatever the
    producer thinks groups these, since it knows and the viewer does
    not."""

    weight: float | None = None
    """How large to draw it, in [0, 1], where something computed one.
    `None` is not zero: it means nothing measured this, and a viewer
    should pick its own default rather than draw a dot."""

    def __post_init__(self) -> None:
        if self.weight is not None and not 0.0 <= self.weight <= 1.0:
            raise ValueError("a weight outside [0, 1] is not a share of anything")


@dataclass(frozen=True)
class EdgeVisual:
    """Hints for drawing one relationship. Never read by a derivation."""

    short_label: str | None = None
    weight: float | None = None
    """How heavily to draw the line. As on a node, `None` means nothing
    measured it."""

    dashed: bool = False
    """Whether the relationship is offered rather than settled -- a
    candidate, a weakened claim. A viewer that ignores this draws a
    solid line, which is wrong but not misleading in the way a wrong
    colour would be."""

    def __post_init__(self) -> None:
        if self.weight is not None and not 0.0 <= self.weight <= 1.0:
            raise ValueError("a weight outside [0, 1] is not a share of anything")
