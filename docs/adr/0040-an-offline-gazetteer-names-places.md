# ADR-0040: An offline gazetteer names places

## Status

Accepted. Part 1 of proposals/0002, item 4.

## Context

Place interests and far stops speak in coordinates. A coordinate is
honest but unreadable; "Kyoto" carries what "35.01,135.77" hides.
Every naming service on the network would break the no-network
premise, and bundling data would put megabytes of someone else's
database in this repository.

## Decision

The owner downloads a GeoNames file themselves (docs/gazetteer.md;
CC BY 4.0, attribution in the docs) and the library only ever reads
it. No file means no names and nothing else changes. The adapter
loads the rows into a half-degree grid and answers nearest() within
a distance, deterministically (ties break on the label); GeoNames
admin columns are opaque codes, so a name travels with its country
code only.

Two privacy rules are part of the decision, not the presentation:

- Anchors are never named. Naming home or work would undo what
  coordinate blurring protects (ADR-0017's spirit); only place
  interests and far stops are candidates.
- Names are never stored. Interests keep their place references and
  naming happens at presentation and narration time, so a rebuild,
  a file swap or a file deletion changes no data (ADR-0013's
  principle applied to somebody else's database).

## Consequences

- `kiseki paths` shows the expected file location; part 2 wires the
  names into profile, report and view display.
- kiseki-core keeps zero runtime dependencies: the whole adapter is
  a TSV reader and arithmetic.
