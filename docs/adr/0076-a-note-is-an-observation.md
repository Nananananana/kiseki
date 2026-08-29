# ADR-0076: A note is an observation, not a state

## Status

Accepted. Corrects ADR-0075 before a producer existed to depend on it.

## Context

The note table keyed a reading by the note. Reading a folder twice
replaced what was there, so the library held the current state of each
note and nothing about how it got there.

That is the mistake this project exists to avoid. One photograph tells
you about its subject; a sequence tells you about the photographer,
and the whole library is built on the second reading. A note has the
same two readings, and the first had been chosen by accident.

The difference is not small. A thought had once and a thought lived
with are identical in a single record. In a trail they are nothing
alike: one reference appearing in March, May and August with its
labels growing is a person staying with something. The same reference
appearing once is a person who wrote a page and moved on.

## Decision

A reading is keyed by the note **and the day**. A note returned to
across six months is six readings. The same note on the same day
replaces, because running the producer twice in an afternoon is not a
second thought.

Schema 8 rebuilds the table -- SQLite cannot widen a primary key in
place -- and carries every existing row across as what it already was:
a first sighting. The v6-to-v7 migration writes the wider key too, so
a database arriving from further back is not built twice.

Readings come back ordered by day, because a trail read out of order
is not a trail.

## Consequences

- The derivations this makes possible are the ones photographs already
  have, in another material: a sitting is a stop, a stretch is an
  outing, a note returned to for months is an anchor. That is the next
  change, not this one.
- Labels arriving together on one day are a co-occurrence in the
  owner's own thinking, which nothing else in this library can see.
- Web pages and watched videos inherit the shape when they arrive. A
  page opened once and a subject returned to for three weeks are
  different things, and only a trail tells them apart.
- It was found by the owner asking why notes were being read as
  states. No test could have found it: the code did correctly what it
  had been told to do.
