# ADR-0060: A night away is one journey

## Status

Accepted. Delivers the overnight trips of proposals/0007, v0.9.

## Context

Outings split on silence, and sleep is silence. Three days in Seoul
arrive as three outings, and every derivation downstream reads them as
three visits to a place the owner keeps returning to. The real library
showed the cost twice: `suggest` offered "go back to Seoul, every two
days, 149 days since", and a holiday three nights long became a place
the owner supposedly sets out from, putting a distant island six
hundred metres from itself.

Both were fixed where they showed -- a cadence needs a month of span
(ADR-0050), a base needs the same (ADR-0055). Those are patches on a
shape the library did not have.

## Decision

A trip is a run of outings that stayed away from every place the owner
sets out from, close enough together in time to be one going, and
spanning at least one night. Away means every stop of the outing sits
at least fifty kilometres from the nearest regular place; one stop near
home ends the run, because a going that passes through the everyday is
two goings. The silence allowed inside a trip is thirty-six hours:
sleep, a slow morning and a late start are one journey; three days at
home between two weekends are not.

Outings are untouched. A trip is derived on top of them, the way
interests are derived on top of readings, so nothing that already
works has to change to gain the shape it was missing.

## Consequences

- The two calibrations become what they should be: guards for the
  ordinary case, not the only defence against a misreading.
- `places` and `suggest` can tell a holiday from a habit by asking
  whether a visit belongs to a trip, rather than by inferring it from
  a span.
- v0.9's retention work has a unit worth keeping: a decade of outings
  is a lot; a decade of trips is a life.
