# 0025. Compare profiles through the current themes

## Status

Accepted

## Context

Profiles accumulate: every `kiseki profile` run keeps its reading
(ADR-0016), and the stated purpose of that history is a trend. But the
vocabulary of a profile is not stable. Theme adoption (ADR-0023,
ADR-0024) replaced member labels with theme names, and any future
recalibration may do the same. A raw comparison of topics across time
would read every renaming as one interest fading and another appearing,
which is a statement about the vocabulary, not about the person.

There is also a floor on how close two readings can be and still say
anything. Two profiles taken in the same week differ mostly by noise:
one more outing, one more caption.

## Decision

- A trend compares the **latest** profile against a **baseline**: the
  most recent profile generated at least `MIN_TREND_SPAN_DAYS` (14)
  before the latest. With no eligible baseline there is no trend, and
  that absence is an answer, not an error.
- Before comparison, every topic in both profiles is mapped **through
  the current theme set**: a topic that is a member of a theme is read
  as that theme; a topic in no theme speaks for itself. When several
  interests map to the same name, the strongest reading is kept.
- The strength of a topic is `score x confidence`: how strongly the
  evidence points, discounted by how far the reading can be trusted.
- Directions: a topic only in the latest is **new**; only in the
  baseline, **faded**; otherwise the strength delta against
  `TREND_DELTA` (0.05) decides **rising**, **declining** or **steady**.
- The derivation is deterministic and calls no model. The thresholds
  are named constants, to be calibrated against the real history once
  it has grown past the minimum span.

## Consequences

- Histories written before a theme change stay comparable after it,
  because both sides are read through the same, current vocabulary.
- The mapping uses only the current theme set. A theme that dissolves
  in a future set will re-scatter its members; the trend then reports
  that scattering honestly rather than papering over it.
- Until the real history spans 14 days, `kiseki trend` correctly
  answers "not enough history". Growing the history is an operational
  habit (a weekly `kiseki profile`), not a code change.
