"""An offline gazetteer read from a GeoNames file, once.

The file is the owner's own download (docs/gazetteer.md): never
bundled, never fetched, and its absence simply means no names. Rows go
into a half-degree grid; nearest() searches the 3x3 neighbourhood
around the point, which covers the tens of kilometres this library
ever asks for while touching a handful of buckets instead of every
row. See ADR-0040.

## Why this reads the file once, and what "once" means

Measured on the real library: `cities500.txt` is 235,375 rows and 40
MB, and the first version of this class parsed all of it into two
objects per row on *every* command that names a place -- 1.6 seconds
each time, and `suggest` did it twice, which was 3.2 of its 3.9
seconds. Nothing else in the command came close. So:

- **Once per process.** The parsed rows are memoised on the file's
  path, size and modification time, so a command that names places in
  two listings reads the file once.
- **Once per file, across processes.** With a cache directory, the
  first read writes a compact copy -- coordinates as a flat array of
  doubles, names as lines of text -- keyed by the source's size and
  modification time, and later processes load that in a fraction of
  the time. Delete the directory to force a re-read; a changed source
  is noticed by its key. No pickle: nothing here can execute.
- **Nothing is built until it is asked for.** Rows are kept as
  primitives; a `GeoPoint` and a `PlaceName` are made only for the
  few hundred candidates inside a search, never for every row.

The answer is the same as before, row for row: the tests hold the
cached and uncached paths to identical results on the same fixture.
"""

from __future__ import annotations

import contextlib
import math
import shutil
from array import array
from dataclasses import dataclass
from functools import lru_cache
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

CACHE_FOLDER = "gazetteer"
COORDINATES_FILE = "coordinates.f64"
NAMES_FILE = "names.txt"


@dataclass(frozen=True)
class _Rows:
    """Every usable row of a gazetteer, as primitives."""

    latitudes: array[float]
    longitudes: array[float]
    labels: tuple[str, ...]
    """`name<TAB>country` per row, split only when a row is a candidate."""

    buckets: dict[tuple[int, int], array[int]]
    """Grid cell to row indices."""

    @property
    def count(self) -> int:
        return len(self.labels)


def _cell(latitude: float, longitude: float) -> tuple[int, int]:
    return (math.floor(latitude / GRID_DEGREES), math.floor(longitude / GRID_DEGREES))


def _bucketed(
    latitudes: array[float], longitudes: array[float]
) -> dict[tuple[int, int], array[int]]:
    buckets: dict[tuple[int, int], array[int]] = {}
    for index in range(len(latitudes)):
        cell = _cell(latitudes[index], longitudes[index])
        found = buckets.get(cell)
        if found is None:
            found = buckets[cell] = array("I")
        found.append(index)
    return buckets


def _parse(path: Path) -> tuple[array[float], array[float], list[str]]:
    latitudes: array[float] = array("d")
    longitudes: array[float] = array("d")
    labels: list[str] = []
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
            latitudes.append(latitude)
            longitudes.append(longitude)
            labels.append(f"{name}\t{columns[COUNTRY_COLUMN].strip()}")
    return latitudes, longitudes, labels


def _cache_folder(cache_dir: Path, path: Path, size: int, mtime_ns: int) -> Path:
    return cache_dir / CACHE_FOLDER / f"{path.stem}-{size}-{mtime_ns}"


def _read_cache(folder: Path) -> tuple[array[float], array[float], list[str]] | None:
    coordinates = folder / COORDINATES_FILE
    names = folder / NAMES_FILE
    if not (coordinates.is_file() and names.is_file()):
        return None
    flat: array[float] = array("d")
    with coordinates.open("rb") as handle:
        flat.frombytes(handle.read())
    labels = names.read_text(encoding="utf-8").split("\n")
    if labels and labels[-1] == "":
        labels.pop()
    if len(flat) != 2 * len(labels):
        return None
    return flat[0::2], flat[1::2], labels


def _write_cache(
    folder: Path, latitudes: array[float], longitudes: array[float], labels: list[str]
) -> None:
    # Older copies of the same source are stale by construction; drop
    # them so a cache directory does not grow with every download.
    parent = folder.parent
    parent.mkdir(parents=True, exist_ok=True)
    stem = folder.name.split("-", 1)[0]
    for sibling in parent.glob(f"{stem}-*"):
        if sibling != folder and sibling.is_dir():
            shutil.rmtree(sibling, ignore_errors=True)
    folder.mkdir(parents=True, exist_ok=True)
    flat: array[float] = array("d")
    for index in range(len(latitudes)):
        flat.append(latitudes[index])
        flat.append(longitudes[index])
    (folder / COORDINATES_FILE).write_bytes(flat.tobytes())
    (folder / NAMES_FILE).write_text("\n".join(labels) + "\n", encoding="utf-8")


@lru_cache(maxsize=4)
def _load(path: Path, size: int, mtime_ns: int, cache_dir: Path | None) -> _Rows:
    """Rows for one version of one file. Memoised on its key."""
    loaded: tuple[array[float], array[float], list[str]] | None = None
    folder = _cache_folder(cache_dir, path, size, mtime_ns) if cache_dir is not None else None
    if folder is not None:
        loaded = _read_cache(folder)
    if loaded is None:
        loaded = _parse(path)
        if folder is not None:
            # A cache that cannot be written costs a re-parse next time
            # and nothing else; the answer does not depend on it.
            with contextlib.suppress(OSError):
                _write_cache(folder, *loaded)
    latitudes, longitudes, labels = loaded
    return _Rows(
        latitudes=latitudes,
        longitudes=longitudes,
        labels=tuple(labels),
        buckets=_bucketed(latitudes, longitudes),
    )


class FileGazetteer:
    """Conforms to Gazetteer; loads a GeoNames tab-separated file."""

    def __init__(self, path: Path, cache_dir: Path | None = None) -> None:
        self._rows: _Rows | None = None
        if not path.is_file():
            return
        stat = path.stat()
        self._rows = _load(path, stat.st_size, stat.st_mtime_ns, cache_dir)

    @property
    def entries(self) -> int:
        return 0 if self._rows is None else self._rows.count

    def nearest(self, point: GeoPoint, within: Distance) -> PlaceName | None:
        if self._rows is None:
            return None
        rows = self._rows
        row, column = _cell(point.latitude, point.longitude)
        close: list[tuple[float, str, PlaceName]] = []
        for cell_row in range(row - 1, row + 2):
            for cell_column in range(column - 1, column + 2):
                for index in rows.buckets.get((cell_row, cell_column), ()):
                    location = GeoPoint(rows.latitudes[index], rows.longitudes[index])
                    meters = point.distance_to(location).meters
                    if meters <= within.meters:
                        name, _, country = rows.labels[index].partition("\t")
                        place = PlaceName(name, country)
                        close.append((meters, place.label, place))
        if not close:
            return None
        return min(close, key=lambda item: (item[0], item[1]))[2]


def forget_loaded() -> None:
    """Drop the per-process memo. For tests that rewrite a fixture in place."""
    _load.cache_clear()
