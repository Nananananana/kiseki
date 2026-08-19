# ADR-0061: Forgetting reaches everything that spoke

## Status

Accepted. Delivers the deletion semantics of proposals/0006 and 0007,
v0.9.

## Context

Every privacy promise in this library assumes the owner can take
something back, and until now they could not. Removing a photograph
from the database left its caption, its subjects, its screen reading,
its indexed text and its embedding exactly where they were. The
profile went on speaking from evidence that no longer existed, and
`ask` could quote a photograph the owner had deleted. proposals/0006
already called that a defect: orphan derived data outliving its
source.

## Decision

One module names the whole path, so it cannot drift: the observation,
the single caption, the screen reading, every stay caption whose
photographs include it, the subjects of those captions, the indexed
documents of all of them, and their embeddings.

Journeys are absent from that list deliberately. Stops and outings are
derived, and a rebuild without the photograph produces a history
without it (ADR-0013); deleting them directly would be amending
derived data, which this library does not do.

Corrections are absent too. "That reading was wrong" stays true after
the reading is gone, and a correction that no longer reaches anything
is reported by the doctor rather than quietly dropped -- the owner's
word outlives the thing it was about.

A plan is counted first and shown, and only a separate word removes
anything. The membership of a stay caption is decided in Python
against the parsed JSON, not with a LIKE against the stored string: an
identifier that merely shares a prefix must not be swept up in someone
else's deletion.

## Consequences

- `ask` cannot quote a photograph that was forgotten, because the
  document it would have quoted is gone in the same transaction.
- The privacy dashboard's counts fall by exactly what the plan said
  they would, which is the check that the path is complete.
- v0.9's retention work can express itself as forgetting: a policy is
  a rule for choosing which photographs to forget.
