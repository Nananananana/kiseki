# ADR-0044: Corrections are appended, applied at read



## Status

Accepted. Delivers proposals/0004, item 2 (part 1 of 2).

## Context

The derivations read the owner better than any stranger could, and
still misread: a generic label becomes an "interest", a mislabelled
photograph feeds the wrong topic. proposals/0004 requires the owner
to have the last word -- without that word ever editing raw
evidence, rewriting a kept profile, or being lost.

## Decision

A correction is one appended record: a reference (the evidence
vocabulary the profile already speaks -- topic:<name>,
caption:<key>, photo:<id>, screen:<id>), a verdict (excluded or
reinstated), a note, a time. The log is append-only; the latest
word per reference wins, so undo is another append. This is the
consent shape (ADR-0032) turned owner-facing.

Application is a pure read-time filter, apply_corrections: an
excluded topic drops its interest, an excluded reference drops that
evidence, and an interest left with no evidence drops -- the
evidence-mandatory invariant survives. Scores and confidences are
not recomputed: the reading is filtered, not re-derived. The
Pipeline filters the fresh reading and every kept profile it reads,
so one log reaches profile, trend, lifecycle, insights, tell, view
and the ask contract's supporting_insights at once. Stored history
is untouched; reinstate, and everything returns.

Reach, stated plainly:

| Surface | Obeys corrections |
|---|---|
| profile, trend, lifecycle, insights, tell, view | yes (this ADR) |
| ask supporting_insights | yes (through insights) |
| ask retrieval evidence | yes (part 2) |
| raw evidence, kept profile bytes, search index | never rewritten |

`kiseki correct <reference> [--note] [--reinstate]` appends;
`kiseki corrections` shows the log and what is excluded now.

## Consequences

- The owner can say "not me" and mean it everywhere, reversibly.
- Part 2 (delivered) carries the same exclusions into ask
  retrieval: an excluded reference maps to its index document
  (caption: -> stay:, photo: -> single:, screen: -> screen:) and
  drops before the facts, the confidence and the window are
  derived. Everything excluded means no model call. The index
  itself is never rewritten.
