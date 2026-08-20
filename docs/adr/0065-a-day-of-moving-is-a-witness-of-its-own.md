# ADR-0065: A day of moving is a witness of its own

## Status

Accepted. The first source after photographs; delivers part of
proposals/0008, v0.11, ahead of the record boundary it will inform.

## Context

proposals/0008 plans several new kinds of evidence and a shared
contract to hold them. Designing that contract from one example would
be designing it from imagination, so the first new source is built
first and the contract is drawn from what it turns out to need.

Daily activity is the right first source. It is the least sensitive
thing a phone knows about a body -- a count of steps per calendar day,
with no positions, no times and no route -- and the owner exports it
from their own device. It is also numeric where every existing source
is textual, which is precisely the axis the contract must stretch
along.

## Decision

`DailyActivity` is a date and up to three numbers: steps, distance,
floors. It knows nothing about photographs, and photographs know
nothing about it.

Schema 6 adds `daily_activity` as a table of its own rather than
columns on an existing one. A new witness does not modify the
furniture of an old one; if this source turns out to be a mistake, the
table is dropped and nothing else notices.

Steps beyond two hundred thousand in a day are refused as a fault in
the export. The ceiling is deliberately absurd: the library refuses
the impossible and never argues with the merely unusual.

Sleep, heart rate and weight are declined, on the record: a step count
is a count of steps, and those are symptoms.

## Consequences

- A library with no activity has an empty table, which the sparseness
  matrix already requires every derivation to survive (ADR-0063).
- The record contract for v0.10 now has two real examples to be drawn
  from rather than one and a guess.
- A trip can say how far it was walked, which nothing could say before.
