# 0023 Gather labels into themes; let co-occurrence vouch for the stretch

## Status

Accepted

## Context

Individual subject labels are honest but narrow: tree, landscape and
hiking trail are one inclination wearing three words. Combining them
raises the risk this library refuses everywhere else -- a claim about
a person that nothing observed supports. A car photographed on
commutes is not evidence of loving the outdoors; a car photographed
wherever the trees and landscapes are might be.

## Decision

**Meaning gathers, co-occurrence vouches.** Labels are embedded (the
first use of the embedding stage reserved in ADR-0014) and clustered
greedily and deterministically, busiest labels first. High similarity
joins on meaning alone. Middling similarity joins only when at least
half of the label's stays are already the cluster's stays: the
stretch from car to outdoors must be earned by where the car actually
appeared. Below the middle threshold, nothing joins. All thresholds
are named constants, calibrated against real data.

**A single label is not a theme.** Singleton clusters are dropped;
the label keeps speaking for itself in the profile.

**Names are decoration; members are substance.** The language model
names each theme from the closed list of its members. An unusable or
absent answer falls back to the busiest member's own label, and the
run finishes either way -- naming failure must never cost the
clustering.

**The store is the progress record, keyed by the label universe.** As
long as the labels have not changed, `kiseki themes` finds its work
already done. A new label changes the key and the set is computed
anew; embedding a few hundred labels costs seconds, so recomputation
is cheap by design.

## Consequences

- Merging themes into the profile -- theme interests aggregating
  their members' sightings, member labels absorbed -- is the next
  issue, and is purely deterministic.
- The thresholds are the tuning surface. If real data shows themes
  too eager or too shy, the calibration is a one-line change with the
  tests pinning the behaviour on either side.
- Theme names are English like every fact; the narrative stage
  renders them in the user's language.
