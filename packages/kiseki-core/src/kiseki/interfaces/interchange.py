"""What other people's tools can read.

Everything this library produces has, until now, been shaped for this
library. `kiseki export` writes `kiseki-interest-export v1`, and a
reader who wanted their journeys on a map, or in a notebook, had to
write a converter first. That is a barrier with nothing behind it: the
data is already in the right shape, it was just wearing the wrong
name.

Two formats, chosen because between them they open almost everything:

**GeoJSON** (RFC 7946). QGIS, Leaflet, Mapbox, kepler.gl, Felt,
geopandas, Google My Maps, and every other mapping tool reads it
without being told anything. Written by hand -- it is JSON with agreed
field names, and a dependency to emit it would be a dependency to
emit `{"type": "Feature"}`.

**CSV** (RFC 4180). pandas, Polars, DuckDB, R, Excel and every
spreadsheet anyone has. Also written by hand, and with the escaping
done by the standard library's `csv` module rather than by
`",".join`, which is the mistake this format invites.

## Coordinates are blurred, and you have to ask twice

This is the part that is not a formatting decision.

Everything else this library writes for the world outside is
coordinate-free by construction: the interest export carries no place
at all (ADR-0047), and the API and view blur what they serve. A map
export cannot be coordinate-free -- a map is coordinates -- so it is
the first thing kiseki has ever written that could put somebody's
doorstep in a file.

So the default is blurred to two decimal places, the same grid the
rest of the library uses: roughly a kilometre, enough to say *around
here* and not *this address*. Precise coordinates need `--precise`,
which is a word somebody has to type, and the file says which it got:

    "kiseki:precision": "blurred"    or    "precise"

A consumer can therefore tell, and so can the owner six months later
looking at a file they no longer remember making. **A file that does
not say how precise it is will be assumed to be precise by whoever
finds it**, and they will be right half the time.

Nothing here is served over the network. These are files the owner
writes on purpose, on their own machine, with a command they typed.
"""

import csv
import io
import json
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.shared.geo import GeoPoint

BLUR_DECIMALS = 2
"""The same grid as `payloads.py`: roughly a kilometre."""

BLURRED = "blurred"
PRECISE = "precise"

PRECISION_KEY = "kiseki:precision"
"""A foreign member, which RFC 7946 section 6.1 allows and tells
consumers to ignore if they do not know it. Prefixed so it cannot
collide with anybody else's."""


def _coordinates(point: GeoPoint, precise: bool) -> list[float]:
    """Longitude first. RFC 7946 section 3.1.1, and the single most
    common way to get GeoJSON wrong -- everything renders, in the sea
    off West Africa."""
    if precise:
        return [point.longitude, point.latitude]
    return [round(point.longitude, BLUR_DECIMALS), round(point.latitude, BLUR_DECIMALS)]


def _moment(value: datetime) -> str:
    """ISO 8601, keeping whatever offset was stored."""
    return value.isoformat()


def _feature(point: GeoPoint, properties: dict[str, Any], precise: bool) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": _coordinates(point, precise)},
        "properties": properties,
    }


def stops_geojson(stops: Sequence[Stop], precise: bool = False) -> dict[str, Any]:
    """Every stay as a point, with what was measured about it."""
    return {
        "type": "FeatureCollection",
        PRECISION_KEY: PRECISE if precise else BLURRED,
        "features": [
            _feature(
                stop.centroid,
                {
                    "started_at": _moment(stop.time_range.start),
                    "ended_at": _moment(stop.time_range.end),
                    "duration_minutes": round(stop.time_range.duration.total_seconds() / 60, 1),
                    "photographs": stop.photograph_count,
                },
                precise,
            )
            for stop in stops
        ],
    }


def outings_geojson(outings: Sequence[Outing], precise: bool = False) -> dict[str, Any]:
    """Every outing as the line its stops drew, in the order they happened.

    A `LineString` and not a route: it joins the places, and says
    nothing about how anybody got between them. An outing of one stop
    is a `Point`, because RFC 7946 requires two positions for a line
    and a one-stop outing is a real thing.
    """
    features = []
    for outing in outings:
        places = [_coordinates(stop.centroid, precise) for stop in outing.stops]
        geometry = (
            {"type": "LineString", "coordinates": places}
            if len(places) > 1
            else {"type": "Point", "coordinates": places[0]}
        )
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "id": outing.id.value,
                    "started_at": _moment(outing.time_range.start),
                    "ended_at": _moment(outing.time_range.end),
                    "duration_hours": round(outing.duration.total_seconds() / 3600, 2),
                    "stops": outing.stop_count,
                    "photographs": outing.photograph_count,
                },
            }
        )
    return {
        "type": "FeatureCollection",
        PRECISION_KEY: PRECISE if precise else BLURRED,
        "features": features,
    }


def anchors_geojson(anchors: Sequence[Anchor], precise: bool = False) -> dict[str, Any]:
    """Every place returned to, as a point with its shares.

    The radius travels as a property rather than as a polygon. A
    circle drawn as a polygon is a claim about a boundary, and an
    anchor has no boundary -- it has a centre and a spread. A consumer
    that wants a circle can draw one from `radius_metres`; one that
    draws the point has not been misled.
    """
    return {
        "type": "FeatureCollection",
        PRECISION_KEY: PRECISE if precise else BLURRED,
        "features": [
            _feature(
                anchor.area.center,
                {
                    "radius_metres": round(anchor.area.radius.meters, 1),
                    "first_seen": _moment(anchor.period.start),
                    "last_seen": _moment(anchor.period.end),
                    "visit_days": anchor.visit_days,
                    "night_share": round(anchor.night_share, 3),
                    "weekday_share": round(anchor.weekday_share, 3),
                    "daytime_share": round(anchor.daytime_share, 3),
                    "photographs": anchor.photograph_count,
                    "confidence": round(anchor.confidence.value, 3),
                    "confidence_sample": anchor.confidence.sample_size,
                },
                precise,
            )
            for anchor in anchors
        ],
    }


STOP_COLUMNS = (
    "started_at",
    "ended_at",
    "duration_minutes",
    "latitude",
    "longitude",
    "photographs",
    "precision",
)


def stops_csv(stops: Sequence[Stop], precise: bool = False) -> str:
    """The same stays, for a spreadsheet or a dataframe.

    `precision` is a column and not a header comment, because a
    comment above a CSV is a comment `pandas.read_csv` drops. Every
    row carries it, and a reader who concatenates two files still
    knows which rows came from where.
    """
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(STOP_COLUMNS)
    for stop in stops:
        longitude, latitude = _coordinates(stop.centroid, precise)
        writer.writerow(
            [
                _moment(stop.time_range.start),
                _moment(stop.time_range.end),
                round(stop.time_range.duration.total_seconds() / 60, 1),
                latitude,
                longitude,
                stop.photograph_count,
                PRECISE if precise else BLURRED,
            ]
        )
    return buffer.getvalue()


def as_json(document: Any) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2)


FORMATS: dict[str, str] = {
    "geojson": "RFC 7946: QGIS, Leaflet, kepler.gl, geopandas, Google My Maps",
    "csv": "RFC 4180: pandas, Polars, DuckDB, R, any spreadsheet",
}

SUBJECTS: dict[str, str] = {
    "stops": "every stay, as a point",
    "outings": "every outing, as the line its stops drew",
    "anchors": "every place returned to, with its shares",
}


def csv_is_available_for(subject: str) -> bool:
    """CSV is offered for stops alone, for now.

    An outing is a line and an anchor is a circle; flattening either
    into one row per feature loses the thing that made it worth
    exporting. Saying so is better than emitting a column called
    `coordinates` holding a string nobody can parse.
    """
    return subject == "stops"


def write(
    subject: str,
    format_name: str,
    stops: Sequence[Stop],
    outings: Sequence[Outing],
    anchors: Sequence[Anchor],
    precise: bool = False,
) -> str:
    """One entry point, so the CLI holds no format knowledge."""
    if format_name == "csv":
        if not csv_is_available_for(subject):
            raise ValueError(
                f"csv carries points, and {subject} are not points. Use geojson for "
                f"{subject}, or csv for stops."
            )
        return stops_csv(stops, precise)
    builders = {
        "stops": lambda: stops_geojson(stops, precise),
        "outings": lambda: outings_geojson(outings, precise),
        "anchors": lambda: anchors_geojson(anchors, precise),
    }
    return as_json(builders[subject]()) + "\n"


def every_position(document: Any) -> Iterable[list[float]]:
    """Every coordinate pair in a GeoJSON document, for checking."""
    if isinstance(document, dict):
        if document.get("type") == "Point":
            yield document["coordinates"]
        elif document.get("type") == "LineString":
            yield from document["coordinates"]
        for value in document.values():
            yield from every_position(value)
    elif isinstance(document, list):
        for item in document:
            yield from every_position(item)
