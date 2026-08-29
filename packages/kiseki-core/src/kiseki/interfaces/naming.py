"""Names for place topics, resolved at display time.

The gazetteer never writes anything: a topic keeps its place
reference, and the name is looked up when a human is about to read
it. No file means no names and nothing else changes. Anchors are
never routed through here at all. See ADR-0040.

A name is coarser than a place. The clustering is right -- a hundred
and fifty metres apart is two places -- and the gazetteer answers
within twenty-five kilometres, so sixteen separate places in one
suburb all come back as the same town. Listed by name they read as
sixteen duplicates of a bug. They are not duplicates; they are one
name and sixteen places, and a listing that says so is honest where
one that repeats the name is not. See ADR-0072.
"""

from collections.abc import Iterable, Sequence
from typing import Any

from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.ports.places import Gazetteer

PLACE_PREFIX = "place:"

NAME_WITHIN = Distance(25_000)
"""How far a named entry may sit from the visited spot: wide enough
for a town's outskirts, narrow enough not to borrow the next city."""


def place_names(topics: Iterable[str], gazetteer: Gazetteer) -> dict[str, str]:
    """Labels for the place topics that resolve; everything else is absent."""
    names: dict[str, str] = {}
    for topic in topics:
        if topic in names or not topic.startswith(PLACE_PREFIX):
            continue
        try:
            latitude_text, longitude_text = topic[len(PLACE_PREFIX) :].split(",")
            point = GeoPoint(float(latitude_text), float(longitude_text))
        except ValueError:
            continue
        place = gazetteer.nearest(point, NAME_WITHIN)
        if place is not None:
            names[topic] = place.label
    return names


def fold_by_name(
    rows: Sequence[Any],
    label_of: Any,
) -> tuple[list[Any], dict[int, int]]:
    """The rows to show, and how many places each one stands for.

    The rows arrive in the order the listing ranks them, so the first
    of a name is the one that earned the line -- the most visited
    place, where the listing is sorted by visits. A row whose name
    does not resolve stands only for itself: two unnamed coordinates
    are two places and there is nothing to join them by.

    The count is keyed by position rather than by label, because two
    rows may legitimately carry the same label in different sections.
    """
    shown: list[Any] = []
    held: dict[int, int] = {}
    seen: dict[str, int] = {}
    for row in rows:
        label = label_of(row)
        if label is None:
            shown.append(row)
            continue
        if label in seen:
            held[seen[label]] = held.get(seen[label], 0) + 1
            continue
        seen[label] = len(shown)
        shown.append(row)
    return shown, held
