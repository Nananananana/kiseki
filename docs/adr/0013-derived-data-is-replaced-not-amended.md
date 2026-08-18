# ADR-0013 Derived data is replaced, not amended



## Status

Accepted

## Context

Three kinds of thing are stored: photographs, outings and anchors.

Photographs are facts. They arrive from an import and accumulate. Nothing the
library does changes one.

Outings and anchors are derived from those photographs by pure functions. They
are not edited, and no user ever changes one directly.

That difference invites a question about the storage interface. Should the
outing repository offer `save`, `update` and `delete`, mirroring the
photographs, or something else?

Offering per-item updates would be misleading. Adding a single photograph in the
middle of a day can merge two outings into one, split one into two, or change
which stops a third contains. There is no sensible way to patch that, and an
interface implying otherwise invites a caller to try.

## Decision

Match the interface to the nature of the data.

`PhotoRepository` accumulates. `save_all` inserts or overwrites by identifier,
so re-importing an overlapping export is harmless. That property matters
because the intended workflow is a periodic bulk import where overlap is normal.

`OutingRepository` and `AnchorRepository` offer only `replace_all`. Recompute
everything, store everything, discard what was there. There is no way to amend
one item, because there is no meaningful way to do so.

Cascading deletes remove a replaced outing's stops and photograph references
along with it. An orphaned stop would silently inflate every later count.

The schema version is checked on open. A database written by a different version
is refused rather than guessed at.

## Consequences

- Re-running the pipeline is always safe and always correct
- No migration logic is needed for derived data; it is thrown away and rebuilt
- Incremental recomputation, when it arrives in v1.0, will be a change of
  strategy above this interface, not a change to it
- Full recomputation costs seconds at the scale of tens of thousands of
  photographs, which is what the intended library size is
- The asymmetry between the interfaces documents the asymmetry in the data,
  which is worth more than a uniform set of methods would be
