# ADR-0007 Derive outing identity from content

## Status

Accepted

## Context

Outings need identifiers so that stops, narratives and later profiles can refer
to them, and so that they can be stored and looked up.

Outings are not entities a user creates and edits. They are derived: the whole
set is recomputed from the photographs every time the library runs. Assigning a
random identifier at creation would mean the same outing receives a different
one on every run, breaking every reference stored against it.

A sequential number is no better, because inserting an older photograph shifts
every subsequent number.

## Decision

Derive the identifier from the sorted photograph identifiers the outing
contains, hashed with SHA-256 and truncated.

```python
OutingId.derive(stops)  # sha256 of the sorted photo ids
```

The same photographs always yield the same identifier, regardless of the order
they were supplied in or the order the stops were built.

## Consequences

- Re-running the whole pipeline over unchanged photographs produces unchanged
  identifiers, so stored references remain valid
- Adding a photograph to an outing changes its identifier. This is intended: an
  outing with a different set of photographs is a different outing, and anything
  derived from the old one should be recomputed rather than silently reused
- Truncating to 64 bits is enough for a personal library; collisions are not a
  practical concern at the scale of tens of thousands of photographs
- The domain layer uses `hashlib`, which is in the standard library and
  therefore permitted by the purity contract
