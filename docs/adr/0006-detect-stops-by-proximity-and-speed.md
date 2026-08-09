# ADR-0006 Detect stops by proximity and speed

## Status

Accepted

## Context

A stop is a stay at one place. The only evidence available is the time and
place of each photograph.

Clustering on distance alone fails in a specific and common way: photographs
taken through a train or car window form a tight sequence in time and a loose
one in space, and a distance threshold generous enough to hold a real visit
together will also swallow several kilometres of railway. The result is a
journey misread as a series of stays.

Clustering on speed alone fails differently. Consumer GPS wanders by tens of
metres while the phone sits still, which produces speed spikes that split a
single visit into fragments.

## Decision

Extend the current stay with the next photograph when either signal holds, and
the silence between them is not too long:

1. The photograph lies within `stay_radius` of the centre of the stay so far
2. Or the speed since the previous photograph is at or below `drift_speed`

A gap longer than `max_gap` ends the stay regardless of either.

Proximity to the running centroid absorbs GPS wander. The speed rule covers
gradual movement across a large site, where each step leaves the radius but
nobody is travelling.

A resulting group is a stop when it lasts at least `min_duration` or contains
at least `min_photographs`. Otherwise its photographs are reported as in
transit. Both conditions exist because either alone is wrong: a single frame
from a moving train would otherwise become a stop, and three photographs taken
in ninety seconds at a shrine plainly are one.

Every threshold is a setting with a documented default, never a constant in the
algorithm. Values tuned against one person's photographs would not survive
contact with anyone else's.

## Consequences

- Photographs taken while moving are reported separately and do not become stops
- GPS wander does not fragment a visit
- A photograph taken shortly before arriving can be absorbed into the stay
  ahead of it, which shifts that stay's start time slightly earlier. This is
  accepted: it reflects being nearby, and the alternative is a spurious stop
- Every photograph appears in exactly one of stops, in transit, or unlocated.
  Nothing is silently dropped
- Tuning is exposed rather than hidden, so a poor result is a configuration
  question rather than a code change
