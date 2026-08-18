# ADR-0045: Comparisons carry their arithmetic



## Status

Accepted. Delivers proposals/0004, item 3 (domain in part 1, the
surface in part 2).

## Context

"What changed since then?" invites an opinion. proposals/0004
requires the opposite: a comparison must state its reasons as
deterministic deltas the reader can inspect -- visit weights,
evidence counts -- down to the evidence references.

## Decision

compare_profiles reads two kept profiles through the theme mapping
and states, per topic: appeared, gone, stronger, weaker or steady --
stronger and weaker past the same delta the trend uses (ADR-0025),
so the two features can never disagree about what counts as
movement. Every entry carries the strength and the evidence count
on both sides, and up to three evidence references from the after
side; the loudest changes come first, deterministically. Nothing is
stored, and no model is consulted; corrections apply because the
profiles are read through the correction filter (ADR-0044).

## Consequences

- Part 2 surfaces it: Pipeline.compare(), `kiseki compare`
  (--from/--to picking the latest kept profile at or before each
  date, defaulting to the trend's pair), and GET /compare, blurred.
- "You go out less" can never be said without the numbers that
  earned it.
