# ADR-0048: Discovery ranks by novelty and importance



## Status

Accepted. Delivers proposals/0004, v0.6 item 1.

## Context

The insights list everything the history holds; a feed must choose.
proposals/0004 reserved a second score for that choice, and
proposals/0006 fixed the vocabulary: confidence is evidence
strength, importance is worth showing, novelty is what changed,
similarity is retrieval closeness -- and they are never one number.

## Decision

`kiseki discover` (and GET /discover) ranks the insights by novelty
times importance, where importance = magnitude, capped at one,
scaled by how much evidence remains (saturating at six references).
A big move on thin evidence waits; a finding with no evidence left
sinks to zero. Confidence is shown on every row and never ranked
on; similarity never enters. The feed keeps its top ten,
deterministically.

No read-state is kept: the feed is derived on demand, stored
nowhere, and is not a notification system. "Previously unseen" is
already what the novelty constants encode; a seen-log would be new
state to maintain, against the avoid list.

## Consequences

- The v0.6 discovery ranking exists without a single new stored
  byte; relabeling and re-weighting stay free.
- Next per proposals/0004: mixed-evidence surfacing.
