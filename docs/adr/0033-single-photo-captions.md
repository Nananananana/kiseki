# ADR-0033: Single-photo captions

## Status

Accepted.

## Context

Stay captioning (ADR-0019) describes stops, and stops are made of
located camera photographs. A large share of the library -- one-off
shots, unlocated photographs, saved images of kind `other`, about
1,200 records in the real library -- belongs to no stop, so no model
ever looks at it, yet those photographs carry preference signal
(FR-507, proposals/0002). Screenshots and documents already have
their own reader (ADR-0030) and are out of scope here.

## Decision

A separate store, `single_captions`, keyed by photo id. Photo ids are
content hashes, so the key survives every rebuild with no derivation
at all -- the property ADR-0019 buys stays, for free here. A separate
table rather than reusing `captions`, because stay keys derive from a
representative selection that part 3 of FR-507 will rebuild, and
single captions must not move when it does.

The run reuses the stage-1 captioner (ADR-0014), one image per
request, and has the shape of every other model run: the store is the
progress record, `--limit` bounds a session, an unavailable model
pauses the run, and a refusal is recorded and never asked again
(ADR-0015).

Eligible photographs are of kind `photo` or `other` (or predate the
kind field, ADR-0028), belong to no stop, have a thumbnail, and are
not withheld: `use_for_preference: false` (ADR-0032) means the model
never sees the photograph at all.

Label vocabulary stays shared: subject extraction (ADR-0020) will
read single captions through a caption key derived from the one
photograph, so themes (ADR-0023) can absorb the labels unchanged.
That confluence is part 2 of FR-507, not this change.

## Consequences

- Lone photographs become describable, resumably, at stage-1 model
  cost; rebuilds never invalidate the work.
- The table is additive; no schema version bump (ADR-0018 shape).
- `kiseki singles` is a new model stage alongside `caption` and
  `screens`.
