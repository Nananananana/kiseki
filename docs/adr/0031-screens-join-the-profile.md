# 0031. Screens join the profile



## Status

Accepted

## Context

Screen readings exist (ADR-0030) and the profile does not see them.
EvidenceKind.SCREENSHOT has been reserved since ADR-0016 for exactly
this moment. The readings are noisy in a particular way: one-off
screenshots (a mailbox code, a form) say little, and settings screens
are about the device, not the person.

## Decision

- A new deterministic service derives interests from the answered,
  non-sensitive, non-settings readings: a label must appear on at
  least MIN_SCREEN_LABEL_COUNT (2) screenshots to become an interest.
  Score is the label's share of the most-seen label; confidence grows
  with the count; evidence cites up to five `screen:<photo-id>`
  references with SCREENSHOT kind.
- The merge is append-only: a topic the captions already read keeps
  its existing interpretation; screens only add topics the journeys
  never showed. Wired through the pipeline behind an optional
  repository, like every other reading.
- Screen labels do not pass through the themes yet: the theme sets
  were clustered from stay subjects, and absorbing a foreign label
  set is its own decision, deferred to the v0.4 entity work.

## Consequences

- `kiseki profile` now answers from journeys, stays and screens, and
  each interest says which. The thresholds are named constants,
  calibrated against the 221 real screenshots.
