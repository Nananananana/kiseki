# ADR-0012 Anchors are observations, not categories



## Status

Accepted. Supersedes ADR-0009 and ADR-0011.

## Context

ADR-0009 classified anchors as `PRIMARY`, `WORKPLACE` or `SECONDARY`, inferring
which from when a place was visited. ADR-0011 narrowed it so that a merely
frequent place produced no anchor at all. Both were attempts to save a scheme
that a real photo library then broke.

Run against two years of one person's photographs, with the three places known
in advance, the classifier produced:

| Place | What it is | Visits | Nights | Classified as |
|---|---|---|---|---|
| A | Home | 10 days | 6 | `PRIMARY` |
| B | Workplace | 52 days | 3 | `SECONDARY` |
| C | Parents' house | 12 days | 0 | not an anchor |

The workplace was visited five times more often than the home and was not
recognised, because this person photographs at work and rarely at home. The
parents' house, visited monthly for over a year, disappeared entirely.

Tuning the thresholds would move the failure rather than remove it. The scheme
assumes a shape of life: one home, one workplace, nights at the former and
weekday afternoons at the latter. Working from home collapses two categories
onto one coordinate. Shift work inverts the night window. A student has no
workplace. Two homes are ordinary. The question is answered differently in
different countries, and a library published for anyone cannot pick one answer.

There was a second failure, downstream. Anchor stops were excluded from outings,
so mislabelling a place removed it from the analysis altogether. A monthly visit
to family is among the clearest preference signals a library can contain, and
the classifier deleted it.

## Decision

Report what was observed, and assign no category.

```python
@dataclass(frozen=True)
class Anchor:
    area: GeoArea
    period: TimeRange
    visit_days: int
    night_days: int
    weekday_days: int
    daytime_days: int
    photograph_count: int
    confidence: Confidence
```

`AnchorKind` is removed. The shares carry more than a label did:

```
(34.7810, 135.4700)  187 days   561 photos   night 100%  weekday  70%  daytime   0%
(34.7020, 135.4960)   58 days   116 photos   night   0%  weekday 100%  daytime 100%
(34.7850, 135.4750)   49 days   415 photos   night   0%  weekday   0%  daytime  94%
```

A reader recognises these without being told which is which, and so can a
language model in v0.2, working from evidence rather than from an assumption
compiled into this library.

Outing assembly no longer takes anchors. Every stop belongs to an outing,
splitting only on elapsed time. Anchors annotate; they do not filter.

## Consequences

- No shape of life is assumed, so the library behaves the same for someone
  working from home, working nights, or living between two places
- Places returned to appear in the analytics, which is the point of measuring
  them
- Home appears among the most returned to places. That is correct as a
  measurement; a consumer wanting to exclude it can match against the anchor
  with the highest night share
- Outing counts rise substantially, because ordinary days are no longer removed
- `secondary_min_nights` is gone, having existed only to serve the categories
- Naming a place becomes the caller's problem, which is where the knowledge to
  do it correctly actually lives
