# Getting your journeys into other tools

Everything else this library writes is shaped for this library.
`kiseki map` writes formats other people's programs already read, so
that looking at your own journeys does not start with writing a
converter.

```bash
kiseki map stops                      # GeoJSON, to stdout
kiseki map outings --out trips.geojson
kiseki map anchors --out places.geojson
kiseki map stops --format csv --out stops.csv
```

| subject | GeoJSON geometry | what it is |
|---|---|---|
| `stops` | `Point` | every stay, with when and how long |
| `outings` | `LineString` (or `Point` for a single stop) | the line an outing's stops drew |
| `anchors` | `Point` + `radius_metres` | every place returned to, with its shares |

## What reads these

**GeoJSON** ([RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946)) — QGIS,
Leaflet, Mapbox, kepler.gl, Felt, geopandas, Google My Maps. Drag the
file in; nothing needs configuring.

**CSV** ([RFC 4180](https://datatracker.ietf.org/doc/html/rfc4180)) — pandas,
Polars, DuckDB, R, Excel, Numbers.

```python
import geopandas

geopandas.read_file("trips.geojson").explore()  # a map in a notebook

import pandas

pandas.read_csv("stops.csv", parse_dates=["started_at"])
```

Both were checked with those libraries rather than with this
repository's own parser — a test that only runs your own reader agrees
with any consistent mistake. `shapely` parses every geometry in the
suite; `geopandas` read the outings file as 19 features while this was
written.

CSV is offered for `stops` only. An outing is a line and an anchor is
a circle, and flattening either into one row loses the thing that made
it worth exporting. Asking for `--format csv outings` says so rather
than emitting a column nobody can parse.

---

## Coordinates are blurred, and you have to ask twice

**This is the part that is not about formats.**

Everything else this library writes for the outside world is
coordinate-free by construction — the interest export carries no place
at all ([ADR-0047](adr/0047-export-is-a-one-way-abstraction.md)),
and the API and the view blur what they serve. A map cannot be
coordinate-free, so `kiseki map` is the first thing kiseki has ever
written that could put your doorstep in a file.

So:

```bash
kiseki map stops                # blurred to ~1 km. the default
kiseki map stops --precise      # exact. a word you have to type
```

and the file says which it got, in a foreign member RFC 7946 section
6.1 allows:

```json
{ "type": "FeatureCollection", "kiseki:precision": "blurred", ... }
```

The CSV carries it as a **column on every row**, not a header comment:
`read_csv` drops comments, and somebody who concatenates two files
still needs to know which rows came from where.

**A file that does not say how precise it is gets assumed precise by
whoever finds it**, and they will be right half the time. Yours says.

These are files you write on your own machine with a command you
typed. Nothing here is served over a network.
