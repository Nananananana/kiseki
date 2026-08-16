"""An offline gazetteer read from a GeoNames file.

The file is the owner's own download (docs/gazetteer.md): never
bundled, never fetched, and its absence simply means no names. Rows
are loaded once into a half-degree grid; nearest() searches the 3x3
neighbourhood around the point, which covers the tens of kilometres
this library ever asks for while touching a handful of buckets
instead of every row. See ADR-0040.
"""

from __future__ import annotations

import math
from pathlib import Path

from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.ports.places import PlaceName

NAME_COLUMN = 1
ASCII_NAME_COLUMN = 2
LATITUDE_COLUMN = 4
LONGITUDE_COLUMN = 5
COUNTRY_COLUMN = 8
MINIMUM_COLUMNS = 9

GRID_DEGREES = 0.5
"""Bucket size: about 55 km of latitude, so a search within a few
tens of kilometres stays inside the 3x3 neighbourhood."""


class FileGazetteer:
    """Conforms to Gazetteer; loads a GeoNames tab-separated file."""

    def __init__(self, path: Path) -> None:
        self._buckets: dict[tuple[int, int], list[tuple[GeoPoint, PlaceName]]] = {}
        self._count = 0
        if not path.is_file():
            return
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                columns = line.rstrip("\n").split("\t")
                if len(columns) < MINIMUM_COLUMNS:
                    continue
                try:
                    latitude = float(columns[LATITUDE_COLUMN])
                    longitude = float(columns[LONGITUDE_COLUMN])
                except ValueError:
                    continue
                if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
                    continue
                name = columns[ASCII_NAME_COLUMN].strip() or columns[NAME_COLUMN].strip()
                if not name:
                    continue
                place = PlaceName(name, columns[COUNTRY_COLUMN].strip())
                cell = _cell(latitude, longitude)
                self._buckets.setdefault(cell, []).append((GeoPoint(latitude, longitude), place))
                self._count += 1

    @property
    def entries(self) -> int:
        return self._count

    def nearest(self, point: GeoPoint, within: Distance) -> PlaceName | None:
        row, column = _cell(point.latitude, point.longitude)
        close: list[tuple[float, str, PlaceName]] = []
        for cell_row in range(row - 1, row + 2):
            for cell_column in range(column - 1, column + 2):
                for location, place in self._buckets.get((cell_row, cell_column), ()):
                    meters = point.distance_to(location).meters
                    if meters <= within.meters:
                        close.append((meters, place.label, place))
        if not close:
            return None
        return min(close, key=lambda item: (item[0], item[1]))[2]


def _cell(latitude: float, longitude: float) -> tuple[int, int]:
    return (math.floor(latitude / GRID_DEGREES), math.floor(longitude / GRID_DEGREES))
