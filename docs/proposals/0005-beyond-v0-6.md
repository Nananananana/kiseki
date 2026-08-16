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

1. Incremental build (moved up from v1.0): ingest already appends
   and every model stage resumes; the remaining full-recompute is
   the journey build. Stops and outings are windowed by silence, so
   a rebuild can start from the last unchanged outing instead of
   photograph one. Derived state stays derived: an incremental
   result must equal the full rebuild, and a test proves it.
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
