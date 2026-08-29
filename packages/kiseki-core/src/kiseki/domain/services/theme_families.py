"""Themes stand above one another, and a listing says each thing once.

The naming model does not produce one flat layer. On a real library it
produced three:

    eating > dining > table
    nature > plant  > tree
    display > screen

Twenty-three theme names are members of other themes. Every layer is a
true reading of the same photographs, so the profile keeps all of them
-- an owner who only ever hears "you are interested in eating" has been
told nothing, and the specific word is the whole point of this library.

What a listing must not do is say the same thing three times. Ranked by
score, the three layers arrive together and fill the page with one
subject. So the fold happens at reading time, as corrections
(ADR-0044), the label stoplist (ADR-0053) and the spatial filter all
do: the strongest of a family is shown, the rest are counted, and
nothing is discarded anywhere. See ADR-0068.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from kiseki.domain.caption.themes import Theme
from kiseki.domain.services.theme_mapping import theme_mapping

MAX_DEPTH = 8
"""How far up a chain to walk before deciding it is a cycle. The real
set is three deep; anything past this is the model naming a loop, and
a loop has no top."""


def family_of(topic: str, mapping: dict[str, str]) -> str:
    """The topmost theme a topic belongs to, or the topic itself.

    A cycle stops at the first repeat, so a set that names a loop gives
    an arbitrary but stable answer rather than hanging.
    """
    seen = {topic}
    current = topic
    for _step in range(MAX_DEPTH):
        above = mapping.get(current)
        if above is None or above in seen:
            return current
        seen.add(above)
        current = above
    return current


def families(themes: Sequence[Theme]) -> dict[str, str]:
    """Every label that belongs to a family, mapped to the family's head."""
    mapping = theme_mapping(themes)
    return {member: family_of(member, mapping) for member in mapping}


def fold_by_family(
    topics: Iterable[str], themes: Sequence[Theme]
) -> tuple[list[str], dict[str, int]]:
    """The topics to show, in order, and how many each one stands for.

    The input is already ranked, so the first of a family is its
    strongest reading. A topic in no family stands only for itself.
    """
    heads = families(themes)
    shown: list[str] = []
    held: dict[str, int] = {}
    seen: dict[str, str] = {}
    for topic in topics:
        family = heads.get(topic, family_of(topic, theme_mapping(themes)))
        if family in seen:
            held[seen[family]] = held.get(seen[family], 0) + 1
            continue
        seen[family] = topic
        shown.append(topic)
    return shown, held
