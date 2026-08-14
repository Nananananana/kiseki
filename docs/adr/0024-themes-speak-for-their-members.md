# 0024 Themes speak for their members

## Status

Accepted

## Context

ADR-0023 computes themes; this record decides what they mean in the
profile. Two questions: does a member label keep its own interest
alongside the theme, and can an ambient label smuggle its ubiquity
into a theme's score.

## Decision

**Absorption, not duplication.** A theme interest aggregates its
members' sightings, with a stay shared by several members counted
once, and the absorbed members stop appearing as solo interests. One
inclination, one line in the profile; the member breakdown remains in
the stored theme set for anyone who asks why.

**Ambient stays ambient, even inside a theme.** ADR-0021's exclusion
applies to a label's contribution everywhere. A theme left with fewer
than two contributing members is not emitted, and the remaining
member speaks for itself again -- a theme must not be a laundering
route for what the profile already refused.

**The pipeline stays model-free.** `kiseki profile` reads the latest
stored theme set; computing themes remains `kiseki themes`' job. No
repository, or an empty one, means labels simply speak solo.

## Consequences

- The profile now says "outdoor" where it said tree, landscape and
  hiking trail -- the combination the owner asked for, earned by
  similarity and co-occurrence rather than assumed.
- Score and confidence of a theme follow the same saturating formulas
  as any subject, over the union of stays.
- The narrative stage inherits themes automatically: they are
  ordinary interests with better names.
