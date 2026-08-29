"""One reading of a theme set, for everything that reads one.

Trend, lifecycle and comparison each turn a theme set into a mapping
from member label to theme name, and each wrote the same line to do
it:

    {member: theme.name for theme in themes for member in theme.members}

Written three times, it was corrected in none of them. Two faults rode
through it on a real library.

A theme name can be generic. The naming model called one cluster
"text" (members: text, document) and another "object" (members:
object, digital object), and every history feature reported them as
topics -- while the profile, which does apply the criterion to theme
names (ADR-0053), did not. The same rule now applies wherever a theme
set is read.

A theme set can hold two themes with the same name. The real one holds
"transport" twice, "text" twice, "vegetable" twice and "code" twice.
Two themes with one name are one theme to a reader, so their members
are merged rather than one silently overwriting the other.

See ADR-0067.
"""

from __future__ import annotations

from collections.abc import Sequence

from kiseki.domain.caption.themes import Theme
from kiseki.domain.services.generic_labels import is_generic


def theme_mapping(themes: Sequence[Theme]) -> dict[str, str]:
    """Member label to theme name, with the generic names left out.

    A member that belongs to several themes keeps the first mapping,
    which is the order the naming model produced -- an arbitrary but
    stable choice, and the same one every reader gets.
    """
    mapping: dict[str, str] = {}
    for theme in themes:
        if is_generic(theme.name):
            continue
        for member in theme.members:
            mapping.setdefault(member, theme.name)
    return mapping


def merged_themes(themes: Sequence[Theme]) -> tuple[Theme, ...]:
    """The same themes, with same-named ones joined and generic ones gone.

    Order is the order the names first appeared, so a reader sees the
    set in the shape the model produced it.
    """
    members: dict[str, list[str]] = {}
    for theme in themes:
        if is_generic(theme.name):
            continue
        seen = members.setdefault(theme.name, [])
        for member in theme.members:
            if member not in seen:
                seen.append(member)
    return tuple(Theme(name=name, members=tuple(labels)) for name, labels in members.items())
