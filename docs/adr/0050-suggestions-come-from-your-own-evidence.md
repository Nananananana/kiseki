# ADR-0050: Suggestions come from your own evidence

## Status

Accepted. Delivers proposals/0004, v0.6 item 4 (the internal
candidates; places beyond the owner's history are v0.8).

## Context

A recommender usually reaches for a catalogue. KISEKI's promise is
the opposite: the first suggestions must come entirely from the
owner's own evidence, with the why attached, or not at all.

## Decision

`kiseki suggest` derives, deterministically and without a model:

- go back: a place with at least three visits and a revisit cadence,
  not visited for more than twice that cadence -- the why is the
  cadence and the days since, from the owner's own journeys. The
  visits must also span at least a month (v0.7 calibration): three
  days in a row on a holiday give a two-day median gap and a year
  of absence, and calling that overdue would be arithmetic
  pretending to be understanding. Trips get their own shape when
  overnight journeys land in v0.9;
- pick up: an interest seen in at least two readings that has gone
  dormant -- the why is the readings count and the baseline
  strength it once held.

The most overdue first, capped at five. Confidence is evidence
volume, saturating at six, and never enters the ordering
differently from what the numbers say. A suggestion's reference
speaks the profile's vocabulary (place:lat,lon or the topic), so
`kiseki correct` declines a suggestion the way it declines a
reading -- the correction log reaches forward too. Local only;
nothing is stored, and no external catalogue exists to consult.

## Consequences

- The first suggestion the owner ever sees is one they already
  earned.
- v0.8 widens the candidates (day-trip reach from the owner's own
  distances, the optional provider boundary) without changing the
  contract: suggestion, why, confidence, evidence vocabulary.
