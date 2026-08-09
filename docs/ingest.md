# Ingesting photographs

`kiseki-ingest` is the reference producer. It reads a directory of image files
and writes a PhotoRecord document plus thumbnails. It is not part of the core;
see ADR-0002.

## Usage

```bash
kiseki-ingest F:/kiseki-data/exports F:/kiseki-data \
  --owner u1 --platform ios --default-offset +09:00 \
  --exclude "WhatsApp*" --photos-only
```

| Option | Purpose |
|---|---|
| `--owner` | Identifier for whoever took these photographs |
| `--default-offset` | UTC offset for files with no `OffsetTimeOriginal` |
| `--exclude GLOB` | Skip matching paths, repeatable |
| `--photos-only` | Drop screenshots and other non-photographic content |
| `--no-preference-consent` | Emit records usable for journeys but not for preferences |

Two files are written: `photo-records.json` and `skipped.json`. Nothing is
discarded silently; every file that does not become a record appears in the
skip report with a reason.

## What is skipped, and why

| Reason | Explanation |
|---|---|
| no DateTimeOriginal | Without a capture time the file has no place in a timeline |
| identical content to … | The same bytes already appeared in this run |
| excluded by pattern | Matched a `--exclude` glob |
| classified as … | `--photos-only` was given and the file is not a photograph |

Duplicate detection is by content hash, so a file copied under a different name
is still recognised. This matters because photo exports routinely contain the
same image more than once.

## Content classification

| Kind | How it is decided |
|---|---|
| `photo` | Camera metadata is present |
| `screenshot` | The name looks like a screenshot, or a lossless file has a screen aspect ratio |
| `other` | Everything else |
| `document` | Reserved, never assigned at this stage |

The name is checked before camera metadata, because an edited or re-exported
screenshot can carry the metadata of the device that exported it.

A photographed receipt, menu or whiteboard is indistinguishable from an ordinary
photograph by metadata alone. It carries a real camera signature, a real
timestamp and a real location. Separating those out needs image understanding,
which arrives with captioning in v0.2. Until then they are classified as
photographs and will influence the analysis.

## Exclusion patterns

A star crosses directory separators, so `backup/*` excludes everything below
`backup`. Patterns are matched against the path relative to the source, and
also against the bare file name, so `*.png` works at any depth.

## Time zones

The contract requires a UTC offset on every timestamp. Cameras and older phones
frequently omit `OffsetTimeOriginal`, so `--default-offset` is mandatory rather
than guessed. If a library spans several time zones, run the tool once per
subset with the appropriate offset.
