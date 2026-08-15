# 0032. Honour the consent mechanically

## Status

Accepted

## Context

PhotoRecord v1 has always carried consent, and the contract promised
the core would honour it mechanically. The core never read it. With
per-photo evidence now real (screens, ADR-0030/0031), the promise
has to become code before v0.3 ships as the privacy release.

## Decision

- `use_for_story: false` is the strongest refusal: the record is
  dropped at ingest and never stored.
- `use_for_preference` is carried on the observation (schema
  version 4, the established None-means-before posture; None counts
  as consent, matching what those records agreed to at the time).
  A withheld photograph still shapes journeys -- that is what the
  flag permits -- but no per-photo reading ever sees it: the screen
  run skips it and reports it as withheld.
- Stay captions read a place through one representative thumbnail;
  excluding withheld photographs from that selection lands with the
  v0.4 single-photo work (FR-507), where representative selection is
  rebuilt. Until then the enforcement boundary is every per-photo
  reader, which today means the screens.

## Consequences

- Existing rows migrate to NULL and behave as before. Consent
  changes take effect on the next export and re-ingest, because the
  producer stamps consent into the records.
