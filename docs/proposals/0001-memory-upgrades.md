# Proposal 0001: The memory upgrades

Status: evaluated. Adopted parts target v0.4; two parts are already
satisfied by the current design; two parts are declined as proposed
and adopted in a different shape.

## Origin

The owner proposed five pillars under the heading "memory", drawing
on the design ideas of memory-layer projects such as Mem0: (1) memory
update, (2) temporal retrieval, (3) entity linking, (4) hybrid
search, (5) memory lifecycle -- with the instruction to survey the
current code first and respect the existing architecture with minimal
change. This document is that survey and the verdicts.

## Verdict at a glance

| Pillar | Verdict |
|---|---|
| 1. Memory update | Already satisfied structurally; in-place updates declined |
| 2. Temporal retrieval | Adopt, v0.4 (the trend is its first instrument) |
| 3. Entity linking | Label half already shipped as themes; place half adopted for v0.4, local-only |
| 4. Hybrid search | Adopt, the v0.4 core and the Phase 2 Q&A foundation |
| 5. Memory lifecycle | Declined as stored state; adopted as labels derived from the trend |

## The ten survey answers

1. **Domain today.** Facts (photographs, captions, subject readings),
   measures (stops, outings, anchors, places, rhythm), and
   interpretations (interests with mandatory evidence and confidence,
   profiles, themes, trends). The proposal's "Episode" has no
   counterpart and maps to `Outing`.
2. **Search today.** None. Retrieval is whole-object: the latest
   profile, the full history, the stored theme set. Nothing queries
   inside a profile or across captions.
3. **Database today.** SQLite, schema version 2. Tables: photos,
   outings, stops, stop_photos, anchors, profiles (JSON documents),
   captions, subjects, theme_sets. Model-expensive artefacts are
   keyed by content and survive rebuilds (ADR-0019/0020/0023).
4. **Ports today.** Repositories, models (captioner, language model,
   embedder), thumbnails, profiles, captions, subjects, themes -- all
   `typing.Protocol`, implementers never import the port, every
   implementation runs one shared contract suite.
5. **Files that change (hybrid search).** New domain values for a
   query and a ranked answer; a `SearchRepository` port; a SQLite
   adapter (FTS5 virtual table + an embedding table); an application
   use case; CLI `ask`/API `/ask`. Derivation services are untouched.
6. **New models.** None. `bge-m3` is already staged and adapted for
   embeddings (ADR-0014, chunked since the runner fix); FTS5 ships
   inside the standard library's sqlite3.
7. **Database changes.** Additive only, like profiles and captions
   before: an FTS5 table over captions and topics, and an embedding
   cache keyed by content hash. No schema version bump expected; an
   incompatible change would follow the explicit-migration rule
   (ADR-0018).
8. **Architectural fit.** A search index is derived data and must be
   rebuildable wholesale (ADR-0013); embeddings are model-hours and
   must be keyed by content so they survive (ADR-0019's rule applied
   to vectors). Answers must cite evidence -- a search hit is a
   pointer to facts, never a new claim (ADR-0016, ADR-0022).
9. **Test plan.** A contract suite for the search port run against
   the fake and SQLite; deterministic ranking tests with the injected
   fake embedder; llm-marked tests for the real embedding path;
   CLI/API tests in the established isolated-paths style.
10. **Impact.** No change to how interests are derived or profiles
    are kept. The blast radius is additive: one port, one adapter,
    one use case, two thin interface surfaces. What screenshots are
    allowed to contribute (v0.3's Privacy Filter) bounds what search
    can ever surface, so v0.3 decides v0.4's ceiling.

## The pillars, one by one

### 1. Memory update -- already satisfied, in-place updates declined

Interests are re-derived wholesale from the stored facts on every
reading (ADR-0013), so new evidence already re-evaluates every
interest, and every reading is kept in the profile history. Updating
a stored interest in place would create a second source of truth and
break "derived data is replaced, not amended". Evidence is immutable
by construction. Nothing to build.

### 2. Temporal retrieval -- adopt (v0.4)

The trend (ADR-0025) is the first temporal instrument over the kept
history. v0.4 extends the same material to questions: recent
interests, interests in a named year, what strengthened lately --
filters over `generated_at` and evidence dates, no new storage.

### 3. Entity linking -- half shipped, half adopted (v0.4, local-only)

The label half exists: themes gather labels into concepts
(ADR-0023/0024). The place half -- reading coordinates as named
places and regions -- is adopted for v0.4 under one hard condition:
any gazetteer is an offline dataset shipped or downloaded once; no
geocoding call at question time. "No network required" includes
questions.

### 4. Hybrid search -- adopt, the v0.4 core

Keyword (FTS5) + semantic (bge-m3) + entity + time filters over
captions, topics and evidence, answering with citations. This is the
Phase 2 question-answering foundation ("where should I go for a day
trip?" starts as a search over what the library already knows).
Survey answers 5-9 above are its implementation sketch.

### 5. Memory lifecycle -- declined as storage, adopted as vocabulary

A stored Active/Stable/Weakening/Dormant state machine is a mutable
truth bolted onto immutable facts, and it duplicates what the history
already knows. Adopted instead as derived labels: the trend already
names new, rising, steady, declining and faded; "dormant" is faded
across several consecutive readings, computed at read time from the
same history, stored nowhere.
