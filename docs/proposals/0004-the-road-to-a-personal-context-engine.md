# Proposal 0004: The road to a personal context engine



Status: Accepted. Refines the v0.5/v0.6 slices of proposals/0003
after the owner's improvement brief (2026-08); the three pillars and
everything shipped through v0.4 stand unchanged.

## The principles, restated as law

Every v0.5/v0.6 feature obeys the boundary that built v0.1-v0.4:

```text
Deterministic layer: facts, measures, profile, trend, insight,
                     confidence, evidence, candidates
AI layer:            narration, explanation, answer phrasing
```

The model explains evidence; it never creates facts, decides
confidence or lifecycle, picks evidence, sets interest scores, or
declares contradictions. Raw evidence is immutable; derived state is
recomputable; corrections are append-only; confidence is computed
from evidence; no raw personal data crosses the sharing boundary;
external providers are never a core dependency; "I don't know" is a
correct answer.

## Decisions from the brief

**Adopted as written**

- Evidence traceability everywhere: every derived thing -- insight,
  answer, comparison, lifecycle, discovery, suggestion -- carries
  references that resolve mechanically to evidence, source and time
  range. "Explainable in prose" is not enough.
- Contradiction is never asserted: v0.6 surfaces *mixed evidence*
  ("nature ran strong; city visits are rising") and keeps
  past/present/changing side by side. One person is not one profile.
- Discovery prefers discoveries: ranked by new, meaningful change,
  confidence, evidence, previously-unseen -- never a notification
  system, never a recency feed.
- Place intelligence is relational: "how does this place relate to
  you", derived from the owner's own evidence -- never a general
  place rating.
- `suggest` is an evidence-based suggestion, not a hunch: it returns
  suggestion, why, evidence, confidence, and is derived personal
  evidence -> insight -> candidate -> recommendation. No suggestion
  may be built from external data alone.
- Interest export is a privacy boundary: themes, scores and trends
  only, one-way abstraction; never raw photos, raw coordinates,
  exact timestamps, screenshot text, identifiers or movement
  history. The schema is explicit and versioned.
- Interest similarity before person similarity: profiles may be
  compared as interest vectors; "similar interests", never "similar
  people". Nothing social ships in v0.5/v0.6.
- The avoid list stands: no SNS, follows, chat, cloud-first,
  microservices, autonomous agents, payments, heavy external APIs,
  vector-DB platforms, LLM-owned judgement, or raw-data sharing.

**Adopted with adaptation**

- The Insight object (v0.5) uses the house vocabulary: `topic` (not
  `subject`, which names what a photograph shows), kind, direction,
  magnitude, first/last seen, confidence, evidence references,
  novelty, derived_from. An insight is never an "AI memory": raw
  evidence -> measures/profile/trend -> deterministic derivation ->
  insight -> narration, and the model cannot invent one.
- Confidence and importance stay separate concepts. v0.5 implements
  confidence only (evidence-derived, as everywhere); importance --
  "worth showing" -- arrives with the v0.6 discovery ranking, and
  confidence is never reused as a feed ranking.
- Corrections (v0.5) reach every derivation: an append-only
  correction store, read at derivation time exactly as consent is
  (ADR-0032's shape), affecting subject derivation, interests,
  profile, trend, insight, ask, discovery and suggest -- and never
  the raw evidence. The reach is documented per feature.
- The ask contract already ships (ADR-0038: answer, confidence, time
  range, evidence; no evidence means no model call). v0.5 adds
  supporting_insights when insights land, and leaves room for
  answer_type and limitations; nothing is removed.
- Lifecycle is already deterministic and boundary-tested
  (ADR-0042). v0.5 adds the arithmetic behind each label to the
  output, so "growing" shows the strengths it compared.
- Prompt-version tracking (v0.6): stored model artifacts gain a
  prompt version beside the model name they already carry, enough to
  answer "which model, which prompt, which contract" -- without
  logging raw personal data.
- The profile-history habit stays manual, but v0.5 surfaces the
  *opportunity*: when enough new evidence has arrived since the last
  kept profile, the CLI says so. No automatic snapshots; derived
  state stays deliberate. Incremental updates remain v1.0.
- `kiseki doctor` (v0.5) tags its deterministic checks with
  categories -- privacy, integrity, consistency, evidence, schema --
  and stays small.

**Deferred**

- importance scoring, external providers, interest similarity across
  people, and incremental context updates are designed for, not
  built, before v0.6/v1.0.

## v0.5 -- discover insights

In experience order, not feature order: the goal is that one thread
works end to end (evidence -> profile -> insight -> ask -> compare).

1. The Insight object and its deterministic derivations, narrated
   with citations (the tell/ask shape). `kiseki insights`.
2. Corrections: append-only store, `kiseki correct`, read by every
   derivation; the reach documented.
3. `kiseki compare` (profiles) with reasons: what changed, and the
   deterministic deltas -- visit counts, theme frequency, revisit
   intervals -- behind each judgement, down to evidence.
4. Lifecycle explanations; ask gains supporting_insights.
5. The privacy dashboard: `kiseki privacy` reports, from counts, how
   the library treats the owner's data -- stored, used as evidence,
   excluded, coordinates stored/exported, screenshot text stored
   (no), raw images sent anywhere (no).
6. Interest export: the versioned, abstracted schema.
7. Snapshot opportunity hints; doctor categories.

## v0.6 -- understand change, suggest

1. Discovery feed: new findings ranked by novelty and importance,
   each with evidence.
2. Mixed-evidence surfacing (the contradiction feature, renamed by
   its behaviour).
3. Personal place intelligence: places related to the owner's
   patterns, from the owner's evidence.
4. `kiseki suggest`: suggestion, why, evidence, confidence.
5. Prompt-version tracking.

## Done means

The owner can ask -- what am I into lately, what changed since last
year, what came back, is anything pulling two ways, why do you think
that, where should I go next, what did you find that I had not
noticed -- and every answer walks the same path:

```text
Evidence -> derived context -> answer
```

The value of KISEKI is not a plausible answer. It is finding, with
evidence, the patterns in your own data that you had not noticed
yourself.
