# ADR-0062: Retention is a rule, not a machine

## Status

Accepted. Delivers the retention of proposals/0007, v0.9.

## Context

A library that only grows eventually holds a decade of somebody's
days, and nobody decided that: it simply happened. proposals/0007
asked for the shape of a decade to be chosen before anyone has one.
The temptation is a background process that trims as it goes.

## Decision

Retention is expressed as rules about what to forget, and the
forgetting is the one that already exists (ADR-0061). Three rules,
every one of them off unless the owner sets it:

- photographs older than a span;
- refusals older than a span, because a refusal is a note about a
  moment and stops being useful long before the photograph does;
- kept readings beyond the most recent few, thinned to the first of
  each month.

The last rule keeps the shape of a history rather than a window of
it. Trend, lifecycle and comparison all read across years; one
reading a month leaves them a decade to read while holding a
fraction of the rows.

Nothing runs on a timer, and nothing is deleted by a default. A
library that quietly discarded the owner's past because a default
said so would break the promise the rest of this code keeps.
`kiseki retention` counts and shows; only `--apply` removes.

## Consequences

- The answer to "what does a decade look like" is a policy the owner
  can read, argue with, and leave switched off.
- Photographs go through the deletion path that reaches everything
  that spoke about them, so retention cannot leave orphans where a
  deliberate deletion could not.
