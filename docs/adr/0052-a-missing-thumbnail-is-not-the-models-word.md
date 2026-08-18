# ADR-0052: A missing thumbnail is not the model's word

## Status

Accepted. Amends ADR-0015 without weakening it.

## Context

Refusals are recorded so a resumable run never asks the same
question twice (ADR-0015). That rule was written for the model's
answer: asking again would get the same refusal. Real data showed
the rule catching something else -- ninety stays refused with "no
thumbnail", because a batch of newly ingested photographs had no
reduced copies on disk. That is not the model's word; it is the
environment's absence, and the environment can change.

## Decision

A refusal that begins "no thumbnail" is recoverable: the reader
never saw an image, so nothing was decided. `kiseki retry` reports
how many such refusals each stage holds, and `--stage X --apply`
deletes exactly those rows, so the next run of that stage asks
again. If the image is still missing, the same refusal is recorded
again -- there is no loop, because only the owner starts one.

The model's own refusals are never taken back. `kiseki doctor` adds
a line when recoverable refusals exist, so the gap is visible
before it silently thins a profile.

## Consequences

- A bad export no longer costs the owner those readings forever.
- The distinction is one prefix today; if the readers grow other
  environmental failures, they name themselves the same way.
