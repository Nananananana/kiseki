# ADR-0002 PhotoRecord is the only input contract

## Status

Accepted

## Context

Photos come from iPhone, Android, cameras, and archives. Each exposes metadata
differently: PhotoKit, MediaStore, EXIF, XMP. Location is sometimes present,
sometimes stripped by the sharing layer, sometimes absent entirely.

If the library read these formats directly, every new source would mean changes
inside the core, and the core would accumulate platform knowledge it has no
business holding.

The library also needs image bytes for captioning, but embedding images in the
input would make a thirty thousand photo dataset unusable in memory.

## Decision

The core accepts exactly one input format: a JSON document conforming to
`schemas/photo-record-v1.json`.

- Thumbnails are referenced by a relative string, resolved through a
  `ThumbnailLoader` port. Image bytes never appear in the contract.
- `location` is optional. Records without it are retained and handled, not
  rejected.
- Each record carries an `owner` and a `consent` block. The core is required to
  honour consent mechanically.
- Record identifiers are content hashes, making re-ingestion idempotent.

Reading EXIF, HEIC, PhotoKit, or MediaStore is the responsibility of producers
outside the core. `kiseki-ingest` is one such producer, provided as a reference
implementation, not as part of the core.

A conformance test kit is published so that a producer written in any language
can verify that its output is acceptable.

## Consequences

- Adding a platform requires no change to the core
- The claim that the core is platform independent is verifiable, and is enforced
  by an import-linter contract forbidding `kiseki_ingest` from importing
  `kiseki.domain`
- Producers must generate thumbnails themselves, which is extra work for them
- The schema must be versioned and kept backward compatible
- Relative thumbnail references mean storage can be moved by changing one
  environment variable, with no data migration
