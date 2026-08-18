# ADR-0011 A frequently visited place is not automatically an anchor



## Status

Accepted. Amends ADR-0009.

## Context

ADR-0009 classified every sufficiently frequented place as one of three kinds,
falling back to `SECONDARY` when nothing else fitted. Running that against two
years of a real photo library exposed the flaw.

The library contained a regular cafe, visited on 49 separate days, and two parks
visited on 25 and 16 days. All three were classified `SECONDARY`, on the
strength of frequency alone. Because anchor stops are excluded from outings, all
three then disappeared from the outings entirely.

The consequence was visible in the measures:

```
distinct places        30
never returned to     100%
returned to at least    0%
```

Every place the person actually returned to had been reclassified as somewhere
they operate from, leaving only one-off trips in the outings. The single measure
that says the most about preference read as its opposite.

The error was treating frequency as the definition of an anchor. Frequency is
necessary but not sufficient. An anchor is somewhere a person acts *from*: they
sleep there, or they work there. A cafe visited every Saturday is somewhere they
chose to go, and choosing repeatedly is exactly the signal the library exists to
detect.

## Decision

Classification may decline. `_classify` returns `None` for a cluster that is
frequented but is neither slept at nor worked at, and such clusters produce no
anchor.

| Kind | Requires |
|---|---|
| `PRIMARY` | Slept at on more days than anywhere else |
| `SECONDARY` | Slept at on at least `secondary_min_nights` days |
| `WORKPLACE` | Mostly weekdays, mostly working hours, never slept at |
| none | Everything else, however often visited |

A place that produces no anchor stays in the outings, where it is measured as a
place returned to.

## Consequences

- The return rate and the one time rate describe what they claim to describe
- Favourite places appear in `most_returned_to`, which is where a reader looks
  for them
- Someone who never photographs home or work will have no anchors at all, and
  outing assembly falls back on elapsed time as described in ADR-0008
- Somewhere genuinely lived at but rarely photographed at night may be missed.
  Under-reporting an anchor costs less than swallowing a favourite place, since
  the first loses a boundary and the second corrupts a headline measure
