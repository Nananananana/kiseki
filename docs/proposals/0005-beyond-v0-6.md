# Proposal 0005: Beyond v0.6 -- living with a context engine



Status: Accepted. Extends proposals/0004 past v0.6; the v0.6 scope
itself stands as 0004 wrote it (discovery ranked by novelty and
importance, mixed-evidence surfacing, personal place intelligence,
evidence-based suggest, prompt-version tracking).

## Why plan past v0.6 now

v0.5 proved the loop: evidence -> derived context -> answer, with
the owner able to question, correct and audit every step. What the
loop has not yet met is time -- years of photographs, model
upgrades, more than one device -- and the two costs that grow with
it: rebuild time and reading drift. v0.7 to v1.0 pay those costs
down before they are felt.

## v0.7 -- live with it

Operational maturity: the weekly habit becomes cheap, and the
library survives its own growth.

1. Incremental build -- held behind a measured trigger. The
   reasoning was sound and the measurement disagreed: at 4,956
   photographs a full `kiseki build` takes 0.3 seconds, `profile`
   1.2 and `index` half a second. Ten times the library is three
   seconds. Until the numbers hurt, an incremental path would add a
   second way for stops and outings to be wrong -- exactly the
   complexity the avoid list warns about, bought with no gain. The
   trigger, so the decision is not taste: when a full build passes
   ten seconds, or the weekly `kiseki refresh` passes a minute
   outside the model stages, the incremental path is written, with
   the equality it must satisfy -- an incremental result equals the
   full rebuild, proven by a test -- as its first requirement. Same
   discipline the vector extension is held to in proposals/0006.
2. `kiseki refresh`: one idempotent command running the whole
   routine (ingest, build, caption, singles, screens, subjects,
   themes, profile, index) with the doctor's summary at the end --
   the runbook, executable, schedulable.
3. The view learns what v0.5 built: insights, compare and the
   discovery feed join the self-contained HTML page (the timeline
   and explorer views deferred from 0004).
4. The model upgrade path, on v0.6's prompt tracking: `kiseki
   reread` re-runs a chosen reading stage under a new model or
   prompt version beside the old readings, and `kiseki compare`
   shows what the upgrade changed before the owner adopts it.
5. Calibration debts, from real data: a stoplist for generic labels
   (date, data, object and kin) at subject-extraction time, and the
   duplicate-topic cleanup -- corrections handle them one by one
   today; v0.7 stops them at the source.

### v0.7, as it actually landed

Prompt-version tracking and `kiseki reread` (ADR-0051), recoverable
refusals and `kiseki retry` (ADR-0052), the doctor's reduced-copy
check, one `kiseki refresh`, the label calibration (ADR-0053, with
theme names judged by the same test), the cadence calibration
(a habit is not a trip), and the findings in the view. What remains
of v0.7 is the reasoning work proposals/0006 assigned to it:
structured model output, evidence-contract validation past the
schema, and prompt regression on the reread path.

## v0.8 -- recommend with evidence (Phase 2 begins)

1. `suggest` learns places: the owner's own reach (the distance
   distribution their outings already show) defines a day-trip
   radius; candidates come from their own anchors, dormant places
   and place intelligence -- personal evidence first, always.
2. The external provider boundary, implemented as designed in 0004:
   a port and an optional adapter (weather, points of interest) that
   the core never imports; providers may re-rank or annotate
   candidates, never create the personal evidence behind them.

## v0.9 -- many devices, long years

1. Several devices merged: PhotoRecord already names owner and
   platform; merging is deduplication by content hash plus a
   provenance note, decided at ingest.
2. Overnight trips: outings that cross nights, with lodging read as
   a stay -- the trip becomes a first-class journey shape.
3. Retention: what a decade of readings should look like, decided
   before anyone has one.

## v1.0 -- public

PyPI, a frozen public API, the conformance kit hardened, a security
pass over `serve`, and versioned documentation. v1.0 adds no new
intelligence; it makes the existing loop dependable for strangers.

## Standing decisions

- Phase 3 (the anonymous interest community) is prepared for only
  through the export schema's version discipline (ADR-0047);
  nothing social is built before v1.0.
- A phone app begins as a Swift producer speaking PhotoRecord v1,
  not as a fork of the core.
- The avoid list of proposals/0004 stands unchanged.
