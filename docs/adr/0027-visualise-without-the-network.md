# 0027. Visualise without the network



## Status

Accepted

## Context

The remaining v0.2 promise is visualisation, and the obvious way to
draw places is a web map: Leaflet over OpenStreetMap tiles. But a
tile map phones home. Every pan and zoom asks a tile server for the
area being looked at, so opening the file would leak the (blurred)
neighbourhood of every photograph to a third party, and the file
would be blank offline. The library's promise is "no account, no
upload, no network required", and an output file is the part of the
library most likely to be opened elsewhere, shown to someone, or
kept for years.

## Decision

- `kiseki view` writes one self-contained HTML file: inline CSS,
  inline SVG, no script sources, no tiles, no CDN, no external
  reference of any kind. The tests pin this as a string property of
  the output (no `http://`, no `https://`, no `<script`).
- The density map draws relative geography on the blur grid
  (two decimals, roughly a kilometre): photograph counts per cell as
  opacity. It shows the shape of a life -- where the weight is, how
  far the excursions reach -- without being a street-level diary.
  The grid applies regardless of `--raw`: a heat map of exact points
  is a location log, not a summary.
- Topic labels (interests, drift) blur by default like every other
  exported surface; `--raw` opts out for the labels only.
- The page also renders the top interests, the outing rhythm by
  weekday and month, and the drift between kept profiles ("not
  enough history" until the history spans the minimum).
- Rendering is a pure function from the measures and readings to a
  string; the command composes and writes the file.

## Consequences

- No real map background. Recommendations shown on an actual map
  (Google Maps links and the like) are a different feature with a
  different privacy posture, and belong to the recommendation work
  (v0.4), where following a link is a deliberate act on one place.
- The file can be attached, archived, or opened in ten years and
  still render; nothing it needs can go away.
