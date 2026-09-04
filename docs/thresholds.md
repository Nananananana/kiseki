# The thresholds, and how to change them

Ten numbers decide what a stay is, what an outing is, and what a place
you return to is. **Four of them were measured. Six were chosen.** All
ten are yours.

```bash
kiseki settings          # what is in force, and where each value came from
```

---

## What each one decides

| setting | default | decides | where the default came from |
|---|---|---|---|
| `stay_radius_m` | 300 | how far a photograph may sit from a stay's centre and still belong to it | measured ([ADR-0006](adr/0006-detect-stops-by-proximity-and-speed.md)) |
| `drift_speed_kmh` | 1.5 | movement slow enough not to end a stay | measured |
| `max_gap_minutes` | 90 | a silence that ends a stay | measured |
| `min_duration_minutes` | 10 | below this, passing through rather than staying | measured |
| `min_photographs` | 5 | at or above this, a stay however brief | measured |
| `max_absence_hours` | 8 | a silence that ends an outing | chosen |
| `cluster_radius_m` | 500 | how far apart two visits are still one place | chosen |
| `min_visits` | 5 | distinct days before a place is an anchor | chosen |
| `night_hours` | `20,6` | which hours count as night | chosen |
| `working_hours` | `10,17` | which hours count as the working day | chosen |

"Measured" means: against **one** photo library — 4,950 photographs,
one person, one country, one way of living. That is more than most
such numbers get, and it is still one library.

---

## Changing them

The same five layers as every other setting, each beating the one
above it:

```text
1  the default
2  kiseki.toml           [derivation]
                         stay_radius_m = 500
                         night_hours = "8,16"
3  .env                  KISEKI_DERIVATION_STAY_RADIUS_M=500
4  the environment       KISEKI_DERIVATION_STAY_RADIUS_M=500
5  the command line
```

The suffix is the unit: `_m` metres, `_kmh` km/h, `_minutes`,
`_hours`. An unrecognised name is **refused rather than ignored** — a
typo that silently does nothing leaves you believing you changed
something.

Rebuilding after a change is safe and cheap: derived data is replaced
wholesale ([ADR-0013](adr/0013-derived-data-is-replaced-not-amended.md)).

```bash
KISEKI_DERIVATION_STAY_RADIUS_M=500 kiseki build
```

---

## When to change which

**`min_photographs`, if you shoot a lot or a little.** Two hundred
frames at one spot meets 5 continuously — every pause becomes a stay.
Three photographs a week never reaches it, and you fall through to
`min_duration`, which is a different rule reached by accident.

**`stay_radius_m` and `cluster_radius_m`, for where you live.** In the
countryside, where the shop is two kilometres from the house, 300
metres splits one visit into several. In a dense city, 500 metres
merges three genuinely different places into one.

**Both rules can be the one that decided**, and it is worth knowing
which. A wander of 800 metres over an hour is held together by
`drift_speed_kmh` whatever `stay_radius_m` says, because 0.8 km/h is
under the 1.5 default. Measured, in the tests: at a one-metre radius,
refusing the drift turns one stay into none; allowing it turns it back.

---

## `night_hours`, which is not a tuning problem

An anchor is **deliberately never named**. The domain says so:

> No attempt is made to say whether this is a home, a workplace, or a
> family house. Those categories depend on how a person lives, and the
> shares below carry more than a label would: a place with a night
> share of 1.0 and a daytime share of 0.0 needs no name for a reader
> to understand it.

That is a good design, and it assumes a schedule. `20,6` and `10,17`
are an office worker's day.

**For a night-shift worker the two shares are inverted**, and the
library describes their workplace with the shares that mean *home*.
Measured, on one library, changing nothing but this setting:

```text
night_hours = 20,6      night share   0%
night_hours = 8,16      night share 100%
```

The same place, described the other way round.

Making the setting reachable does not fix that. It makes it possible
to fix, and says out loud that the default assumed something.
