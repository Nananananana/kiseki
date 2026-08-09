# PhotoRecord v1

The only input KISEKI accepts. The schema lives at
`schemas/photo-record-v1.json` and is the normative definition; this page
explains the reasoning behind it.

## Example

```json
{
  "schema_version": "1.0",
  "records": [
    {
      "id": "sha256:a3f2c9d81b4e7f60a3f2c9d81b4e7f60a3f2c9d81b4e7f60a3f2c9d81b4e7f60",
      "captured_at": "2025-05-03T10:24:31+09:00",
      "location": { "lat": 35.0094, "lon": 135.6669, "accuracy_m": 12 },
      "location_source": "measured",
      "media_type": "image",
      "content_kind": "photo",
      "thumbnail_ref": "2025/05/a3f2.jpg",
      "place_label": null,
      "is_favorite": true,
      "owner": { "owner_id": "u1", "device_id": "d1", "platform": "ios" },
      "consent": { "use_for_preference": true, "use_for_story": true },
      "source": { "exporter": "kiseki-ingest", "version": "0.1.0" }
    }
  ]
}
```

## Fields

| Field | Required | Notes |
|---|---|---|
| `id` | yes | `sha256:` followed by 64 lowercase hex characters |
| `captured_at` | yes | ISO 8601 with a mandatory UTC offset |
| `location` | no | Object or `null` |
| `location_source` | conditional | Required when `location` is an object |
| `media_type` | yes | `image` or `video` |
| `content_kind` | yes | `photo`, `screenshot`, `document`, `other` |
| `thumbnail_ref` | yes | Relative reference, never an absolute path |
| `place_label` | no | Human readable name if the producer knows it |
| `is_favorite` | no | Defaults to false |
| `owner` | yes | `owner_id` required |
| `consent` | yes | Both flags required |
| `source` | no | Producer identification |
| `extra` | no | Free form, ignored by the core |

## Design rules

### Identifiers are content hashes

Re-ingesting the same photo must not create a duplicate. Deriving the id from
the file content makes ingestion idempotent, which matters because the intended
workflow is a periodic bulk import where overlap is normal.

### Timestamps carry an offset

Android reports capture time in the device's local zone, iOS in another. A bare
local timestamp cannot be ordered across devices, and ordering is the entire
premise of this library. A record without an offset is rejected rather than
guessed at.

### Location is optional

A large share of real photos carry no coordinates. Rejecting them would discard
usable timing information, so they are accepted and handled: they can still be
assigned to an outing by time, and in v1.0 their position can be interpolated
from a companion device.

### location_source is not decorative

`measured` and `interpolated` must never be mixed. Interpolated coordinates are
usable for reconstructing a journey but are excluded from anchor estimation,
because a guessed position must not shape the model of where someone lives.

### Thumbnails are referenced, not embedded

A thirty thousand photo import with embedded base64 images is not workable.
The reference is relative, resolved against the configured thumbnail root, so
moving storage to another drive is a configuration change with no data
migration.

### content_kind exists because screenshots exist

Screenshots, photographed documents, receipts and menus are common and carry a
location that says nothing about preference. They are kept for completeness and
excluded from analysis.

### Consent is part of the data

Photos from a companion device are someone else's records. Expressing consent
in the contract lets the core honour it mechanically rather than relying on the
caller to filter first. `use_for_story: false` drops the record entirely;
`use_for_preference: false` keeps it for journey reconstruction only.

## Writing your own producer

The core never reads EXIF, HEIC, PhotoKit or MediaStore. Any program that emits
this JSON is a valid producer, in any language.

`packages/kiseki-ingest` is a reference implementation for EXIF, not part of
the core. An import-linter contract forbids it from importing the core domain,
so the independence is verified rather than asserted.

A conformance test kit is provided in `packages/kiseki-conformance` for
checking your own output.

## Versioning

`schema_version` is a constant, currently `1.0`. Additive changes that keep
existing documents valid raise the minor version. Any change that invalidates
an existing document requires a new major schema file, published alongside the
old one.

Producer specific fields belong in `extra`, not as new top level keys; the
schema rejects unknown properties so that typos surface immediately.
