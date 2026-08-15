# 0028. Carry the content kind

## Status

Accepted

## Context

PhotoRecord v1 has always declared what a record is -- `photo`,
`screenshot`, `document` or `other` -- and the contract promised that
non-photographs are "kept for completeness and excluded from
analysis". The core never honoured that: `PhotoObservation` dropped
the field on ingest, so the exclusion held only by accident, because
the reference producer skips most non-photographs at its own door
(no `DateTimeOriginal`, no record). v0.3 opens that door -- non-photo
records will become interest evidence -- so the accident must become
a rule first.

## Decision

- `PhotoObservation` carries `content_kind` as an opaque string from
  the contract, `None` for records stored before the field existed
  (the same posture as `thumbnail_ref`, ADR-0018). By the rules of
  their time, such records were camera photographs.
- The photos table gains the column in schema version 3. This is the
  first chained migration: a version 1 database walks 1 -> 2 -> 3 on
  connect, one explicit step at a time; an unknown version is still
  refused.
- Journey reconstruction sees camera photographs only: rebuild
  filters on the observation's own answer (`joins_journeys`), so
  stops and anchors are never shaped by a screenshot's location. A
  screenshot has a location -- where the device was when it was made
  -- but not one that was chosen, and choice is what a journey is
  made of. This exclusion is permanent; what v0.3 lifts is the other
  half, non-photographs as interest evidence.

## Consequences

- Existing databases migrate on the next command, no action needed;
  existing rows read as `None` and keep behaving as photographs.
- New kinds only arrive with a re-ingest from a producer that emits
  them, which is the next step (the producer currently refuses most
  non-photographs for lacking a capture time).
