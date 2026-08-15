# Runbook: refreshing the library

The periodic loop that keeps the profile current. Everything is
idempotent: records are keyed by content hash, so exporting
overlapping periods and re-ingesting them is the normal way to work.
Personal paths never go in this repository; put them in `.env` or
`kiseki.toml` (see docs/cli.md, "Where things go").

## 1. Export from the phone

Copy the new period from the photo library into a dated folder under
your exports directory -- and copy the Screenshots album too, if you
want screenshots read as interest evidence (v0.3). Saved and received
images are welcome for the same reason.

## 2. Produce records

```powershell
uv run kiseki-ingest <exports-dir> <run-dir> `
  --owner me --platform ios --default-offset +09:00 `
  --time-fallback-mtime
```

`--time-fallback-mtime` lets screenshots and saved images in: they
rarely carry EXIF time, so they borrow the file-modified time and say
so in `extra.time_source` (ADR-0029). Check `skipped.json` after --
a photograph in there means a genuinely timeless file.

## 3. Take in and rebuild

```powershell
uv run kiseki ingest <run-dir>/photo-records.json
uv run kiseki build
```

Non-photographs are stored but never shape stops or anchors
(ADR-0028), so the journey numbers only move with new photographs.

## 4. Model stages (hours, resumable)

```powershell
uv run kiseki caption     # new stays only; safe to interrupt
uv run kiseki subjects
uv run kiseki themes      # recomputes only when the label set changed
uv run kiseki screens     # screenshots: category and labels only
```

## 5. Read and keep

```powershell
uv run kiseki profile     # keep one reading; weekly is the habit
```

The kept history is what `trend` compares; readings served over HTTP
or written by `view` are never kept.

## 6. Evaluate

```powershell
uv run kiseki report      # counts moved as expected?
uv run kiseki trend       # drift, once the history spans 14 days
uv run kiseki view        # open the HTML: density, interests, rhythm
uv run kiseki tell        # a cited narration, in Japanese
```

`examples/refresh.ps1` runs steps 2-5 in one go.
