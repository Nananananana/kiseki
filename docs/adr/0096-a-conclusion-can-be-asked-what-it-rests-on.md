# ADR-0096: A conclusion can be asked what it rests on

## Status

Accepted. Completes Phase 1 of #435. Follows proposal 0010, which
argued for the provenance graph before the hypotheses, and ADR-0040,
which decided that a place reaching prose is named and never located.

## Context

The library has always kept provenance and could never show it. An
`Insight` refuses to exist without naming what it was derived from, but
that name is a tuple of strings inside a row: something a person can
read and a program cannot traverse. A reader told *flight is new, on
six sightings* had no way to ask **which six**.

The domain model, the store and the builder landed in #437, #439, #440
and #443. Nothing exposed them, so nothing used them.

## Decision

**Two commands, and they answer different questions.**

```text
kiseki graph          what is held, by role and by source
kiseki graph --build  rebuild it from what is derived now
kiseki graph --json   {"nodes": [...], "edges": [...]}
kiseki why <id>       what one conclusion rests on
```

`why` is the reader's word, and the question the whole structure exists
for. On the owner's library it answers in the shape that matters:

```text
  flight is new
  confidence     1.00
  rests on       6 readings
  read from      kept_reading, screen

    2026-08-15  screen   screen:sha256:37e996...
    ...
  because        trend, lifecycle, profile:2026-08-29T13:50:34
```

**Rebuilding, not accumulating.** Every id comes from what a node *is*,
so `--build` writes the same graph twice and the store updates rather
than duplicates. A graph that grew a second copy of everything on each
run would be useless within a week.

**It needs no model.** Deliberate, and the reason it is worth having:
an orchestrator deciding whether to give this library a GPU can read
the whole of its reasoning first, and a library whose explanation
required the thing being scheduled would be no use to a scheduler.

**`why` reads a neighbourhood, not the whole graph.** Three steps --
conclusion, interest, reading, and one spare. Chosen, not measured: it
is how deep this library's chains go. Loading 2,628 nodes to answer a
question about one is the wrong amount of work by three orders of
magnitude, and a test breaks the walk to one step to prove the number
is doing something.

**A missing node is a named failure, not an empty answer.** Silence
would read as *this rests on nothing*, which is a different and much
worse claim.

## No blurring flag, and that is the point

Every other document this library writes takes `--raw`, because every
other one can carry a coordinate. This one cannot: a node may not carry
one in its id any more than its label, so there is nothing to coarsen.

**A document with no dangerous field is better than a document with a
dangerous field and a careful default.** ADR-0095 is the argument --
seven payloads defaulted to raw and no test noticed for three releases.
The graph is the first document here designed after that, and it is
designed so the question cannot arise.

## What the real library taught, in order

Each of these was invisible to the fixtures and cost one run to find.

1. **A topic can itself be a place.** Every test used topics like
   *camping*; `place:34.70,135.50` is an ordinary interest here, so the
   first build raised on the interest node.
2. **Twelve of six hundred insights cite no evidence**, all `dormant` --
   findings about an absence, with nothing recent to point at. The graph
   was right to refuse them; the builder was wrong not to read
   `derived_from`, which already named the kept reading.
3. **The readings were undated.** `InterestEvidence` knows when it
   observed what it observed and the builder dropped it, so the first
   real answer read *undated* six times. A provenance that cannot say
   when is half an answer.

## Consequences

- The orchestrator can be handed `{"nodes": [...], "edges": [...]}`
  with the drawing hints already on it, and no coordinate in it.
- `graph --build` is a separate act rather than part of `refresh`,
  because `refresh` stops at its first failing stage and a graph that
  only rebuilt on a clean run would be stale exactly when something is
  wrong -- which is when somebody asks why.
- Nothing is served over HTTP yet. A route is a promise, and this shape
  is one release old.
