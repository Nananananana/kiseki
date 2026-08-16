"""Names for place topics, resolved at display time.

The gazetteer never writes anything: a topic keeps its place
reference, and the name is looked up when a human is about to read
it. No file means no names and nothing else changes. Anchors are
never routed through here at all. See ADR-0040.
"""

from collections.abc import Iterable

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
