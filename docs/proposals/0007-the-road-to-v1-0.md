# Proposal 0007: The road to v1.0, and evidence beyond photographs

Status: Accepted. Re-plans v0.8 to v1.0 after v0.7 shipped, adds
v0.10 and v0.11, and answers the owner's question about other kinds
of history -- web pages, watched videos -- with a boundary before a
feature. Supersedes the version assignments in proposals/0005 and
0006 where they disagree; every avoid list still stands.

## What v0.7 taught, and what it changes about planning

Three of v0.7's items were not planned: recoverable refusals, the
doctor's reduced-copy check, and the grouped-citation fix. Each came
from running the library on a growing library of photographs, and
each was cheap because the tools around it were honest -- the
privacy dashboard exposed a wiring gap, the golden dataset exposed a
starvation, the answer check exposed its own false alarm.

So the plan below leaves room: each version reserves its last issue
for what the previous version's data says. A roadmap that is full is
a roadmap that cannot learn.

## v0.8 -- Recommend with evidence (Phase 2)

1. `suggest` learns places (proposals/0005): the owner's own outing
   distances define a day-trip radius; candidates come from anchors,
   dormant places and place intelligence -- personal evidence first.
2. The external provider boundary (proposals/0004): a port and an
   optional adapter the core never imports. Providers may re-rank or
   annotate; they never create the evidence behind a suggestion.
3. Cross-timeline analysis with drift (proposals/0006): co-occurrence
   reported as co-occurrence, the absence of causal proof said aloud,
   no judgement of better or worse.
4. `kiseki demo`: a throwaway sandbox with synthetic evidence, so
   every derivation can be seen working end to end without touching
   the owner's library. Born from a real failure -- a demo run read
   the real database because an .env path outranked --data-root -- and
   it makes the whole engine explorable by anyone, including CI.
5. A narration check, the ADR-0054 posture applied to `tell`: a story
   that names a place the evidence never mentioned is a defect,
   reported beside the story. Observed once already: a model decorated
   a Breton stay with a nearby town nobody visited.
6. Reserved for what v0.7's data says.

## v0.9 -- Many devices, long years

1. Several devices merged: deduplication by content hash plus a
   provenance note, decided at ingest.
2. Overnight trips: outings that cross nights, lodging read as a
   stay -- the trip becomes a first-class journey shape, and travel
   places stop being mistaken for habits (v0.7 calibration made that
   safe; this makes it right).
3. Retention: what a decade of readings should look like, decided
   before anyone has one.
4. Deletion semantics (proposals/0006): removing evidence names how
   far the removal propagates; orphan derived data is a defect.
5. Privacy regression tests in CI: no raw coordinate served unasked,
   no network call introduced, no screenshot text stored, no personal
   data committed.
6. Reserved.

## v0.10 -- More than photographs: the boundary

No new source is taken in until the shape that holds it exists --
and the shape is added beside the photographs, never through them.

The owner's rule, adopted: adding a source must not touch the design
that already works.

    PhotoRecord  --+
    WebRecord    --+
    VideoRecord  --+--> Evidence --> Personal context
    SearchRecord --+

1. Records are siblings, not subclasses. PhotoRecord v1 is frozen:
   its schema, its conformance kit and its ingest path stay exactly
   as they are, and no new source may require an edit to them. Each
   new record type arrives as its own contract plus its own adapter,
   and the adapters converge inside the core, on the evidence
   vocabulary the derivations already speak -- a time, an optional
   place, consent, and a reading of categories and labels. If a new
   source's design turns out wrong, it is deleted without the
   photographs noticing. The convergence point is internal, so the
   producers never have to agree with each other, only with the
   core.
2. The new-evidence-type checklist (proposals/0006) becomes a gate
   with an owner-visible answer: source, schema, privacy
   classification, provenance, timestamp and spatial semantics,
   retention, deletion, derived outputs, confidence, export policy.
   A source without ten answers does not land.
3. Provenance and dependency graphs: every derived artifact records
   its sources and versions, so a model, prompt or algorithm change
   names exactly what needs recomputing. With more than one source
   this stops being a nicety.
4. `kiseki privacy` and `kiseki doctor` count per source, so the
   owner sees what each kind of history contributes and costs.
5. Reserved.

## v0.11 -- More than photographs: the first new sources

1. Web history, as a reading and never as a record: a producer reads
   the owner's own export, a model turns each page into a category
   and topic labels, and the URL, the title and the text are
   discarded at ingest -- the ADR-0030 shape, raised to a rule for
   every text-bearing source. What is stored is what a screenshot
   reading stores: a category, labels, a time.
2. Watched videos, the same way: channel and title read into
   category and labels, then dropped. No watch counts, no
   identifiers, no titles at rest.
3. Sensitive categories stay label-silent by construction, as
   screen readings already are: what someone searches in distress,
   logs into, or pays for is not interest evidence.
4. Cross-source retrieval: an answer's evidence names the source it
   came from (the v0.6 retrieval provenance, widened), and the
   golden dataset gains cases where the right evidence is in another
   source than the question's words suggest.
5. Insights, suggest and compare read every source through the same
   derivations -- one profile, several kinds of witness.
6. Reserved.

## v1.0 -- Public

PyPI, a frozen public API, the hardened conformance kit, a security
pass over `serve` with the checklist from proposals/0006, API DTOs
separate from domain entities, and versioned documentation. v1.0
adds no new intelligence.

## Standing decisions, unchanged

- Phase 3 (the anonymous interest community) is prepared for only
  through the export schema's version discipline (ADR-0047).
- A phone app begins as a Swift producer speaking the record
  contract, not as a fork of the core.
- The incremental build waits for its measured trigger
  (proposals/0005); the vector extension waits for its
  (proposals/0006).
- Every new source is a producer outside the core. The core reads
  records; it never reaches for the world itself.
