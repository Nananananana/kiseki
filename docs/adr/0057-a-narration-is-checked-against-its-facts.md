# ADR-0057: A narration is checked against the facts it was given

## Status

Accepted. Extends ADR-0054 to the narration stage; delivers the
narration check of proposals/0007, v0.8.

## Context

The narration stage hands the model a closed, numbered list of facts
and asks for prose that cites them (ADR-0022). Nothing checked that
the prose kept the bargain, and the real library showed two ways it
does not.

The model wrote its citations as a range, "[F10-F16]" -- which the
answer check, knowing only brackets and commas, would have called
uncited. And where the facts said 82 per cent of places were never
returned to, the story said 18 per cent were revisited: arithmetic
that is right and a claim that is not in evidence. A library whose
promise is "only what the facts say" has to notice the difference.

## Decision

validate_narration reports three defects, deterministically and
without a model: the narration cites nothing; it cites a fact that
does not exist; it states a number no fact states. Ranges are read as
the facts they name, because real narrations write them and a check
that cries wolf is worse than no check (the lesson of ADR-0054's
first day).

Numbers of a single digit are not checked: they appear everywhere and
mean little.

The narration is never rewritten. The model said what it said; the
check says what is wrong with it.

## Consequences

- The subtraction the model performed is visible rather than
  invisible. Whether such a claim should be refused rather than
  reported is a later decision, made from how often it happens.
- The same shape now guards both prose surfaces, `ask` and `tell`,
  with one rule each reader can understand.
