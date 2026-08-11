# ADR-0008 Assemble outings around anchors, with silence as a fallback

## Status

Accepted

## Context

An outing is one departure from an anchor and return to it. That definition
depends on knowing where the anchors are, but anchors are estimated from where
stops concentrate, which depends on having stops grouped. The two depend on
each other.

There is also a plain data problem: many people do not photograph their own
home, so there may be no stop inside an anchor to mark the return.

## Decision

Accept anchors as an argument rather than computing them here, and add a
fallback that works without them.

A stop inside any anchor ends the outing in progress and is reported separately
in `at_anchor`. Otherwise, a silence longer than `max_absence` starts a new
outing.

The mutual dependency is resolved by running two passes at the application
level, not by introducing a cycle in the domain: estimate provisional anchors
from stop density, assemble outings, re-estimate anchors from those outings,
reassemble.

`max_absence` defaults to eight hours so that a night away ends the outing.
Grouping consecutive outings that span a night is what `Trip` does, in v1.0.

## Consequences

- The service is usable before anchor estimation exists, which is why v0.1 can
  ship stop extraction and outing assembly before issue #12
- Without anchors, an outing may include stops at home, because there is nothing
  to distinguish them. The result is still a correct grouping by time
- An errand taken after returning home is a separate outing only if the return
  itself was photographed, or if the gap exceeds `max_absence`
- Every stop is either inside an outing or listed in `at_anchor`. Nothing is
  dropped
