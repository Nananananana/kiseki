"""A self-contained view of the measures and readings.

One HTML file that talks to no one: no map tiles, no CDN, no script
sources. Opening it requires a browser and nothing else, which keeps
"no account, no upload, no network required" true of the outputs as
well as the library. Coordinates appear only on the blur grid, and
topic labels blur by default. See ADR-0027.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from html import escape

from kiseki.application.pipeline import Report
from kiseki.domain.interests import Profile
from kiseki.domain.photo.observation import PhotoObservation
from kiseki.domain.services.trend_derivation import MIN_TREND_SPAN_DAYS
from kiseki.domain.trends import TrendReport
from kiseki.interfaces.payloads import BLUR_DECIMALS, blurred_place

MAP_WIDTH = 760
MAP_HEIGHT = 460
TOP_INTERESTS = 12
CELL_DEGREES = 10.0**-BLUR_DECIMALS
"""One density cell is one blur-grid cell: the map never draws finer
than what the library is willing to say about a location."""

MIN_CELL_PIXELS = 3.0
"""However far the map spans, a cell stays visible. A country-wide
library otherwise renders sub-pixel cells and the map looks empty."""

_STYLE = """
body { font-family: system-ui, sans-serif; margin: 2rem auto;
       max-width: 820px; color: #222; }
h1 { letter-spacing: 0.3em; }
section { margin: 2.5rem 0; }
svg { background: #f4f2ee; }
rect { fill: #35507a; }
.row { display: flex; align-items: center; gap: 0.6rem; margin: 0.3rem 0; }
.row .label { flex: 0 0 16rem; overflow: hidden; text-overflow: ellipsis;
              white-space: nowrap; }
.row .track { flex: 1; background: #eee; }
.row .bar { display: block; height: 0.7rem; background: #35507a; }
.row .nums { flex: 0 0 14rem; color: #777; font-size: 0.85rem; }
.chart { display: flex; align-items: flex-end; gap: 0.4rem; flex-wrap: wrap; }
.chart .col { display: flex; flex-direction: column; align-items: center;
              font-size: 0.7rem; color: #555; }
.chart .fill { width: 1.4rem; background: #35507a; }
.note { color: #777; }
"""


def density_cells(photos: Sequence[PhotoObservation]) -> dict[tuple[float, float], int]:
    """Photograph counts per blur-grid cell; unlocated ones are left out."""
    counts: Counter[tuple[float, float]] = Counter()
    for photo in photos:
        if photo.location is None:
            continue
        cell = (
            round(photo.location.latitude, BLUR_DECIMALS),
            round(photo.location.longitude, BLUR_DECIMALS),
        )
        counts[cell] += 1
    return dict(counts)


def render_view(
    photos: Sequence[PhotoObservation],
    report: Report,
    profile: Profile,
    trends: TrendReport | None,
    blur: bool = True,
) -> str:
    """One page: density, interests, rhythm, drift. Blur by default."""
    body = "".join(
        (
            _density_section(density_cells(photos)),
            _interest_section(profile, blur),
            _rhythm_section(report),
            _trend_section(trends, blur),
        )
    )
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        "<title>KISEKI</title>\n<style>" + _STYLE + "</style>\n</head>\n<body>\n"
        "<h1>KISEKI</h1>\n" + body + "\n</body>\n</html>\n"
    )


def _section(title: str, body: str) -> str:
    return f"<section><h2>{escape(title)}</h2>{body}</section>"


def _density_section(cells: dict[tuple[float, float], int]) -> str:
    title = "Where photographs were taken"
    if not cells:
        return _section(title, '<p class="note">no located photographs</p>')

    latitudes = sorted({latitude for latitude, _ in cells})
    longitudes = sorted({longitude for _, longitude in cells})
    low_lat, high_lat = latitudes[0], latitudes[-1]
    low_lon, high_lon = longitudes[0], longitudes[-1]

    stretch = math.cos(math.radians((low_lat + high_lat) / 2))
    span_lat = high_lat - low_lat + CELL_DEGREES
    span_lon = (high_lon - low_lon + CELL_DEGREES) * stretch
    scale = min(MAP_WIDTH / span_lon, MAP_HEIGHT / span_lat)
    width = math.ceil(span_lon * scale)
    height = math.ceil(span_lat * scale)
    peak = max(cells.values())

    natural_x = CELL_DEGREES * stretch * scale
    natural_y = CELL_DEGREES * scale
    side_x = max(natural_x, MIN_CELL_PIXELS)
    side_y = max(natural_y, MIN_CELL_PIXELS)

    rects = []
    for (latitude, longitude), count in sorted(cells.items()):
        x = (longitude - low_lon) * stretch * scale - (side_x - natural_x) / 2
        y = (high_lat - latitude) * scale - (side_y - natural_y) / 2
        opacity = 0.15 + 0.85 * count / peak
        rects.append(
            f'<rect x="{x:.1f}" y="{y:.1f}"'
            f' width="{side_x:.1f}" height="{side_y:.1f}"'
            f' opacity="{opacity:.2f}"><title>{count} photograph(s)</title></rect>'
        )
    svg = (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        + "".join(rects)
        + "</svg>"
    )
    note = (
        f'<p class="note">{sum(cells.values())} located photograph(s) on a'
        f" ~1 km grid; darker is denser</p>"
    )
    return _section(title, svg + note)


def _interest_section(profile: Profile, blur: bool) -> str:
    title = "Read as interests"
    if not profile.interests:
        return _section(title, '<p class="note">no interests yet</p>')
    rows = []
    for interest in profile.ranked()[:TOP_INTERESTS]:
        label = blurred_place(interest.topic) if blur else interest.topic
        width = max(2, round(interest.score * 100))
        opacity = 0.35 + 0.65 * interest.confidence
        rows.append(
            '<div class="row">'
            f'<span class="label">{escape(label)}</span>'
            '<span class="track">'
            f'<span class="bar" style="width:{width}%;opacity:{opacity:.2f}"></span>'
            "</span>"
            f'<span class="nums">score {interest.score:.2f},'
            f" confidence {interest.confidence:.2f}</span>"
            "</div>"
        )
    return _section(title, "".join(rows))


def _bars(counts: dict[str, int]) -> str:
    peak = max(counts.values(), default=0)
    columns = []
    for name, value in counts.items():
        filled = round(80 * value / peak) if peak else 0
        columns.append(
            '<div class="col">'
            f'<div class="fill" style="height:{filled}px"></div>'
            f"<span>{escape(name)}</span><em>{value}</em>"
            "</div>"
        )
    return '<div class="chart">' + "".join(columns) + "</div>"


def _rhythm_section(report: Report) -> str:
    body = (
        "<h3>By weekday</h3>"
        + _bars(report.rhythm.by_weekday)
        + "<h3>By month</h3>"
        + _bars(report.rhythm.by_month)
    )
    return _section("When outings happen", body)


def _trend_section(trends: TrendReport | None, blur: bool) -> str:
    title = "Drift between readings"
    if trends is None:
        return _section(
            title,
            '<p class="note">not enough history: the trend needs two profiles'
            f" at least {MIN_TREND_SPAN_DAYS} days apart</p>",
        )
    if not trends.trends:
        return _section(title, '<p class="note">nothing moved between the two readings</p>')
    header = (
        f'<p class="note">{trends.baseline_at.date().isoformat()} to'
        f" {trends.latest_at.date().isoformat()}</p>"
    )
    rows = []
    for trend in trends.trends:
        label = blurred_place(trend.topic) if blur else trend.topic
        rows.append(
            '<div class="row">'
            f'<span class="label">{escape(label)}</span>'
            f"<span>{escape(trend.direction.value)}</span>"
            f'<span class="nums">now {trend.strength:.2f},'
            f" was {trend.baseline:.2f}</span>"
            "</div>"
        )
    return _section(title, header + "".join(rows))
