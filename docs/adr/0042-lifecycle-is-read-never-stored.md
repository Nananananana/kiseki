# ADR-0042: Lifecycle is read, never stored



## Status

Accepted. Delivers proposals/0002, item 6; v0.4 is feature-complete.

## Context

proposals/0001 decided that lifecycle would be derived labels, not a
stored status machine: a status must be maintained, invalidated and
migrated, while a derivation is recomputed for free. The trend
(ADR-0025) already compares the latest reading with an old enough
baseline; what it cannot say is what the history before that
baseline knew.

## Decision

Lifecycle extends the trend across the whole kept history. The trend
directions map straight over -- rising is growing, steady is stable,
declining is declining, faded is dormant -- and the older history
adds the two stages the trend cannot see: a topic the trend calls
new but the pre-baseline history already contained has returned, and
a topic missing from both ends but present once upon a time is
dormant too. Every stage carries the topic's latest strength and in
how many kept profiles it appeared.

`kiseki lifecycle` (with --json) and GET /lifecycle read it; place
topics are named at display time (ADR-0040) and blurred over HTTP as
usual. Until two profiles sit far enough apart the answer is an
honest "not enough history" -- the weekly `kiseki profile` habit is
the data this feature reads, and its quality grows with the history.

## Consequences

- Nothing is stored, nothing migrates: relabeling logic can change
  freely, and a rebuild changes no history.
- proposals/0002 is feature-complete; next is the v0.4.0 release.
