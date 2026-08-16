"""In-memory gazetteer, for tests and examples."""

from __future__ import annotations

from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.ports.places import PlaceName


class FakeGazetteer:
    """Serves names from a fixed list; conforms to Gazetteer."""

    def __init__(self, entries: list[tuple[GeoPoint, PlaceName]] | None = None) -> None:
        self._entries = list(entries or [])

    def nearest(self, point: GeoPoint, within: Distance) -> PlaceName | None:
        close = [
            (point.distance_to(location).meters, place.label, place)
            for location, place in self._entries
            if point.distance_to(location).meters <= within.meters
        ]
        if not close:
            return None
        return min(close, key=lambda item: (item[0], item[1]))[2]
