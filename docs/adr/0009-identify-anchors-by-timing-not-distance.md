# ADR-0009 Identify anchors by timing, not by distance



## Status

Accepted

## Context

The library needs to know where a person is based, in order to tell an outing
from ordinary life and a destination from a neighbourhood.

The obvious approach is to take the home as a configuration value and treat
anything beyond some radius as travel. Three things are wrong with it.

It asks the user for the single most sensitive coordinate they have, and then
that value has to live somewhere: in a config file, in a database, in a backup.
For a project whose stated position is that it holds no personal data, that is
the wrong direction.

It does not survive people moving house, and it cannot represent someone with
more than one base, which is common: a family home, a partner's flat, a place
kept in another town.

And a fixed radius means different things in different places. Fifty kilometres
from central Tokyo is still Tokyo; fifty kilometres from a rural town is two
towns over.

## Decision

Estimate anchors from the stops themselves, using when a place is visited
rather than how far away it is.

Group stops that fall within `cluster_radius` of a running centre. Keep the
groups visited on at least `min_visits` distinct days. Then classify:

| Kind | Signal |
|---|---|
| `PRIMARY` | The place slept at on the most days |
| `SECONDARY` | Slept at on at least `secondary_min_nights` days, but not the most |
| `WORKPLACE` | Mostly weekdays, mostly working hours, never slept at |

"Slept at" means a stop whose start or end falls in `night_hours`, which is
20:00 to 06:00 and therefore wraps past midnight. Photographs taken at 23:00
and at 02:00 are both evidence of being somewhere overnight; a window that ran
from midnight would miss the first and is the more common one to reach for.

Visits are counted as distinct days, not as stops. Photographing the same place
morning and evening is one day of evidence, not two.

Anchors carry the period over which the evidence was gathered, so that a home
someone has since left remains a true statement about the time it covers.

## Consequences

- No coordinate is ever configured, stored as a setting, or asked for
- Several anchors are supported from the start, which matches how people
  actually live
- Somewhere visited once, however distant or however long the stay, is never an
  anchor. A three week holiday stays a holiday
- Someone who never photographs their home will have no primary anchor. This is
  correct rather than a failure: the library reports what the evidence supports.
  Outing assembly already has a fallback for that case, see ADR-0008
- Classification depends on ordinary working patterns. Night shift work would be
  misread, and the settings exist so that such a user can adjust the windows
- A person who has moved will produce two residential anchors with different
  periods. Deciding which is current from the period is left to the caller in
  v0.1; a sliding window re-estimate is v1.0 work
