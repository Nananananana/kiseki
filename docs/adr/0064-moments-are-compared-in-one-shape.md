# ADR-0064: Moments are compared in one shape

## Status

Accepted. Fixes what the sparseness matrix of ADR-0063 found on its
first run.

## Context

A photograph carries the offset its camera knew; a profile carries
whatever the clock said when it was derived; a command asks "how long
ago" with the clock it has now. Python refuses to subtract an aware
moment from a naive one, correctly, because the answer would be a
guess.

Six modules had each written the same private helper to sidestep this,
under the same name, and four derivations had not. The consequence was
invisible: on the developer's own library every stored timestamp
happened to be naive, so everything agreed. The matrix seeded a library
whose timestamps carried offsets -- which any producer might write --
and seven commands fell over at once: suggest, trend, lifecycle,
insights, discover, compare and export. A lifecycle also compared an
aware moment with a naive one for equality, which is always false, and
quietly lost the baseline it had just been handed.

## Decision

One helper, in the domain's shared vocabulary: `naive` for arithmetic,
`days_between` for the question actually being asked, and `same_moment`
for identity. Aware moments are converted rather than truncated, so an
offset that said midnight in Tokyo does not become midnight in London.

Stored text is untouched. A timestamp is written as it was given, with
its offset, so the API and the view still say what the camera said;
only the comparison drops the zone. Every question this library asks
about time is asked within one person's life, and answers the same way
in any zone.

## Consequences

- A producer that writes offsets no longer breaks seven features.
- The six private copies delegate to the one helper, so the next
  derivation inherits the behaviour instead of reinventing it.
- The matrix that found this now guards it, on every source
  combination.
