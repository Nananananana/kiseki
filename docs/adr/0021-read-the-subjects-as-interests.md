# 0021 Read the subjects as interests, and exclude the ambient by share

## Status

Accepted

## Context

The subject readings (ADR-0020) give every stay a handful of concrete
labels. Turning them into interests raises two questions the place
derivation (ADR-0017) did not have. Which labels are interests at all
-- buildings and people appear in most photographs of a life, and "an
interest in buildings" is the anchor problem wearing a new coat. And
how much evidence should an interest carry, when a common label may
have hundreds of sightings.

## Decision

**One label, one interest, with PHOTOGRAPH evidence.** Each answered
reading contributes one sighting per label, dated by the earliest
photograph of its caption and referencing the caption itself. Labels
are normalised (underscores to spaces) before grouping. This is where
interests gain human-readable topics, as ADR-0017 promised: the label
describes what was photographed.

**Ambient labels are excluded by share, not by list.** A label in
more than a quarter of the readings describes the world the
photographs were taken in, not a choice. The threshold is a named
constant, and the test is data-driven: what counts as ambient in one
person's library is a genuine interest in another's. The exclusion
waits for a minimum number of readings, because with few readings
every label is in most of them and a share test would empty the
profile.

**The formulas follow ADR-0017's shape.** Score saturates with
distinct stays; confidence is the product of enough stays and enough
spread in time. A subject seen on a single day earns a modest score
and zero confidence -- a single photograph is complete evidence of a
sighting (FR-507) and no evidence yet of a durable interest.

**Evidence is capped at the ends of the pattern.** An interest
carries the earliest sighting and the most recent ones, up to ten.
The full record stays in the caption and subject stores; what travels
with the interest is for showing a person why, not for storage.

**The pipeline merges, the derivations stay apart.** Place interests
and subject interests are computed by separate services and joined
into the one profile. Their topics cannot collide: places are named
`place:...`, subjects are bare labels.

## Consequences

- `kiseki profile` now answers with meaning as well as coordinates,
  which is the first output a person can recognise themselves in.
- The ambient threshold and the evidence cap are tuning points, named
  and tested, adjustable without touching the shape.
- Trend still waits: it needs profiles compared across time, and the
  history the repository keeps is its raw material.
