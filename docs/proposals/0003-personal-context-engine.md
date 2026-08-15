# Proposal 0003: The personal context engine (v0.5-v0.6)

Status: accepted direction, August 2026. Sequencing: after
proposals/0002 (v0.4) completes; nothing here preempts it.

## Origin

An owner-written proposal ("Personal Memory / Context Engine")
evaluated against the constitution. Its stated principles --
evidence first, derived state over mutable memory, local-first, the
model as an interpreter over a closed fact set -- already are the
constitution (ADR-0010, ADR-0013, ADR-0016, ADR-0022, ADR-0025), so
most of it lands as extensions of what exists rather than new
machinery. The goal it names is kept verbatim: ask KISEKI about
yourself and get, with evidence, changes you had not noticed.

## Adopted for v0.5

- Insight engine: deterministic findings derived from the measures,
  the kept profiles and the trend (growth, decline, revisit,
  novelty, routine, density, exploration, theme emergence), each
  carrying evidence and a derived confidence. The model narrates
  them in the shape of ADR-0022 and never invents one.
- Ask answer contract: `kiseki ask` (proposals/0002, item 2) answers
  as answer + confidence + time range + evidence, with the
  confidence computed from the evidence, never asked of the model.
- User corrections: an append-only correction store (not_relevant,
  wrong_subject, exclude_from_interest, ...) that derivations
  honour, in the shape of consent (ADR-0032). Raw evidence stays
  immutable; a correction is a new fact about the old fact.
- compare_profiles: a structured "what changed" answer (new, rising,
  declining, returned, places) as an extension of trend (ADR-0025).
- Timeline, evidence explorer, export: read-only presentations of
  stored evidence through view, API and payloads, blurred by
  default; export never carries raw coordinates or screenshot words.
- Privacy dashboard and audit: stored / used / excluded counts, and
  `kiseki doctor` checks (raw text present? withheld photograph used
  as evidence? raw coordinates exposed?), all deterministic.

## Adopted for v0.6

- Derived lifecycle labels (new, growing, stable, declining,
  dormant, returned), computed from the profile history and never
  stored -- as proposals/0001 already decided.
- Contradiction surfacing ("the evidence is mixed") and
  returned-interest detection, both read from the kept history.
- Discovery feed: significant, new, high-confidence insights only; a
  command and a view section, never notifications.
- Place intelligence and place similarity, after place entities
  (proposals/0002, item 4); internal evidence only.
- Recommendation foundation (`kiseki suggest`) and interest export /
  similarity: the Phase 2 and Phase 3 seams, with shareable data
  limited to themes, scores and trends.
- Prompt-version tracking on new model artifacts, joining the model
  name they already carry.

## Already satisfied structurally

Profile snapshots are the kept profile history (`kiseki profile`);
comparison is trend; interest confidence is already derived and
bounded (ADR-0016, ADR-0017, ADR-0021); the closed fact set for
narration is ADR-0022; and the content-hash keys of captions,
subjects and single captions already give the expensive artifacts
their incremental survival across rebuilds.

## Modified or declined

- A separately stored evidence-quality score: declined. It would be
  a second confidence axis; recency and repetition belong inside the
  existing confidence formulas where they are not already.
- Incremental context update: design care only in v0.5-v0.6 (keep
  content-derived keys, do not couple derivations to whole-library
  passes where a windowed pass would do); implementation stays at
  v1.0.
- Everything on the proposal's own avoid list (social network,
  cloud-first, autonomous agent, payments, microservices) stays
  avoided, for the reason the proposal gives: the advantage is the
  evidence, the time axis and the privacy, not the infrastructure.

## Preconditions

The history-reading features (lifecycle, returned interests,
contradiction, comparison) are only as good as the kept history: the
weekly `kiseki profile` habit is the data they will run on. v0.5 can
start without waiting for it; their quality grows as the history
does.
