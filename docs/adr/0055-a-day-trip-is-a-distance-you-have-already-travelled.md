# ADR-0055: A day trip is a distance you have already travelled

## Status

Accepted. Delivers proposals/0007, v0.8: `suggest` learns places.

## Context

Every recommender has to decide what counts as near. The usual
answer is a number somebody chose -- fifty kilometres, an hour by
train -- which describes the average of everyone and nobody in
particular. KISEKI has better evidence: the owner's outings already
say how far they go in a day, and how often they stay inside it.

## Decision

The reach is read from the outings themselves: the distance each one
covers, summarised by the share that describes most of them
(REACH_SHARE, four in five). "Within reach" therefore means "you have
gone this far, and usually no further".

Distance is measured from whichever regular place is nearest.
A life has more than one place it returns to, and the demo showed
what a single centre costs: two places tied for most visited, the
wrong one chosen, and somewhere six kilometres from home judged
fifteen away. Every place with three visits or more is one the
owner comes from.

The centre is the place the owner is most often -- the most visited
place in their own history. No address is asked for and none is
stored.

A day trip is offered when a place sits inside that reach, was
visited once or twice, and has not been visited for half a year: a
place that never became a habit, and might have. Places with a rhythm
belong to `go back` (ADR-0050), and the two shapes never compete for
the same place.

The why is arithmetic, as everywhere: the distance, the share it sits
inside, and how long it has been.

Ordering by distance was wrong, and the real library said so: within
any reach, the next street over is always nearest, so the nearest
three always won and nothing was ever discovered. Day trips are
ordered by how long it has been -- the reach has already decided what
is too far -- and only one is offered per part of town, because three
lines naming one neighbourhood is a list rather than a suggestion.
## Consequences

- The first place suggestion the owner ever sees is measured against
  their own life rather than an average of strangers.
- v0.8's optional provider boundary can annotate these candidates --
  weather, opening hours -- without ever creating one.
- Nothing here reaches outside the library, so the suggestion works
  on a machine with no network, like everything else.
