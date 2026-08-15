# 0029. Borrow the time from the file

## Status

Accepted

## Context

The contract refuses records without a capture time, and refuses to
guess one (docs/photo-record.md): a record without a position in
time cannot take part in a journey. That rule, applied at the
producer, silently discarded every screenshot and saved image --
they rarely carry EXIF -- which was harmless while non-photographs
were unused, and stops being harmless in v0.3, where they become
interest evidence. On the real library, all 62 skipped files were
exactly this: JPEGs without DateTimeOriginal, most likely saved or
received images.

## Decision

- `kiseki-ingest --time-fallback-mtime` lets a record without
  DateTimeOriginal borrow the file's modified time. The borrowed
  value is not a guess: it is a measured filesystem fact, read with
  the machine's own UTC offset, so the contract's offset rule holds.
- The borrowing is opt-in and applies to non-photographs only. On a
  camera file the absence of DateTimeOriginal is an anomaly, and an
  anomaly should surface as a skip, not be papered over.
- A record that borrowed declares it: `extra.time_source` is
  `"file-modified"`. A consumer that cares about time provenance can
  tell the two apart forever.
- Classification therefore happens before the time check in
  `build_record`; what kind of file it is now decides whether the
  missing time is fatal.

## Consequences

- The modified time reflects when the file reached this machine (an
  export, a sync), which for screenshots and saved images is usually
  close to, and never before, the moment of interest. Journeys are
  unaffected either way: non-photographs never shape stops or
  anchors (ADR-0028).
- Re-running the export with the flag recovers the previously
  skipped files with their kinds, ready for the v0.3 reader.
