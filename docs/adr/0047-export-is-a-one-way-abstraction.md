# ADR-0047: Export is a one-way abstraction

## Status

Accepted. Delivers proposals/0004, item 6.

## Context

Phase 3 of the roadmap imagines interests meeting other interests.
Whatever shape that takes, the boundary must exist long before the
feature: an explicit, versioned statement of the most that ever
leaves the machine -- decided now, while nothing is asking for it.

## Decision

`kiseki export` produces kiseki-interest-export, version 1: the
corrected profile's interests (topic, score, confidence, first and
last seen at month granularity) and the lifecycle stages, sorted
deterministically. application/exporting.interest_export is the
single definition point of the schema, and the version number is
part of the document.

What can never cross, by construction:

- a place topic, named or not -- a list of places is a movement
  history;
- an evidence reference, photo id or any other identifier;
- an exact timestamp (months only; the export date is a date);
- a coordinate, a screenshot word, a raw image.

Corrections apply, because the export reads the corrected profile;
the reading is taken with keep=False, so exporting never adds to the
kept history. The export is a deliberate act: a command with an
--out flag, and deliberately not a served endpoint.

## Consequences

- Anything Phase 3 builds must fit through this schema or change it
  by a visible version bump.
- proposals/0004's v0.5 has one item left: snapshot opportunity
  hints and doctor categories.
