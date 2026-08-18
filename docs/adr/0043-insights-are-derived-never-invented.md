# ADR-0043: Insights are derived, never invented



## Status

Accepted. Opens v0.5 (proposals/0004, item 1).

## Context

v0.5 turns KISEKI from answering questions into making findings: "a
new interest appeared", "an old one came back", "this one is
fading". The danger is obvious -- a model asked to "find insights"
will find some, whether or not the data holds them. proposals/0004
forbids exactly that: an insight is never an AI memory.

## Decision

An insight is a deterministic derivation over the kept history,
built on the lifecycle (ADR-0042) and the trend (ADR-0025):

- The kinds are a closed list -- new, returned, rising, declining,
  dormant, enduring -- classified from the lifecycle stages, with
  magnitude taken from the underlying arithmetic (the trend delta,
  or the topic's strength).
- Novelty is a fixed constant per kind, so the ordering (novelty,
  then magnitude, then topic) is arithmetic and a test can pin it.
  It is not importance: "worth showing" is a separate concept that
  arrives with the v0.6 discovery ranking.
- Confidence and evidence are reused from the latest profile's
  interests (themes expanded to their members), never recomputed --
  the same evidence-derived number the profile already carries.
- derived_from names the sources, so Why? -> evidence -> source ->
  time range is mechanical.
- Not everything is a finding: a long-gone dormant topic and a weak
  stable one are inventory, and produce no insight.

Like the trend and the lifecycle, insights are recomputed on demand
and stored nowhere; a model may later narrate them, and may never
add to them.

## Consequences

- Part 2 surfaces them: Pipeline.insights(), `kiseki insights`,
  GET /insights. Part 3 narrates them and feeds `ask`.
- Relabeling logic can change freely; no migration ever.
