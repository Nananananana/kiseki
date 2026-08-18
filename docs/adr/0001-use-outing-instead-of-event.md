# ADR-0001 Use Outing instead of Event



## Status

Accepted

## Context

The central concept of this library is a group of photos taken during one
excursion. The obvious English word is "event", and early sketches used it.

Three problems appeared:

1. `Event` already has a strong meaning in software: something that happened at
   an instant, usually dispatched and handled. A reader encountering
   `EventRepository` would reasonably expect a message log.
2. Domain events are a standard DDD building block. Using `Event` for a
   different concept would make the codebase actively misleading to anyone
   familiar with the pattern.
3. "Event" also has a calendar meaning, which becomes relevant once weather and
   local happenings are integrated in v1.0.

Alternatives considered were `Trip`, `Journey`, `Excursion`, and `Session`.

`Trip` was rejected as the general term because it implies distance and
overnight stays. It is reserved for a narrower concept: a sequence of outings
spanning at least one night. Keeping both words lets us distinguish a day out
from a weekend away without qualifiers.

`Session` was rejected for the same reason as `Event`: it is already taken.

## Decision

Use `Outing` for one departure from an anchor and return to it.

Use `Trip` only for a sequence of outings involving at least one night away.

Do not use `Event` anywhere in the domain, including in comments, table names,
and API fields. If domain events are introduced later, the name remains free
for them.

## Consequences

- The vocabulary is unfamiliar at first glance and needs the glossary in
  `docs/ubiquitous-language.md`
- `Outing` and `Trip` must be kept distinct in every layer, including the
  database schema and the REST API
- The word `Event` stays available for its conventional meaning
