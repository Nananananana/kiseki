# ADR-0046: Privacy is a report, not a promise

## Status

Accepted. Delivers proposals/0004, item 5.

## Context

Every privacy claim this library makes is enforced somewhere in
code: consent flags decide what may become evidence (ADR-0032),
screen readings have no text field (ADR-0030), the gazetteer names
nothing at rest (ADR-0040), served coordinates blur by default
(ADR-0026). What the owner lacked was one place to see all of it,
against their own numbers.

## Decision

`kiseki privacy` (and --json) reports, from counts read out of
storage: what is stored (photographs and how many are located,
captions and refusals, screen readings and how many are
label-silent, subject readings, kept profiles, corrections and how
many exclude right now), what the owner has withheld
(use_for_preference), and what is never stored by construction --
screenshot text, place names, anchor names, story-withheld records
(discarded at ingest), outbound copies. Deterministic, storage-read
only, no model, nothing stored by the report itself.

The dashboard is not served over HTTP: it is the owner's local
view, and serving it would add surface without adding a reader.

## Consequences

- "Trust the docs" becomes "run the command against your own data".
- The doctor's categorised checks (proposals/0004, item 7) can point
  here when a count looks wrong.
