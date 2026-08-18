# Proposal 0006: Retrieval and reasoning, extended



Status: Accepted. Folds the owner's next-roadmap brief (2026-08)
into proposals/0004 and 0005. Nothing here replaces them: the v0.6
scope, the avoid list, and "v1.0 adds no new intelligence" all
stand. This proposal assigns the brief's ideas to versions, adapts
a few, and names what is declined.

## The vocabulary, fixed

Evidence (an observed fact), Derived Data (deterministically
computed from evidence), Interpretation (meaning derived from
evidence and measures), Retrieval (finding the evidence a question
needs), Reasoning (assembling an answer over derived context),
Provenance (where a derived thing came from), Uncertainty (what is
and is not established). And four scores that are never one:
confidence (evidence strength), importance (worth showing), novelty
(previously unseen or changed), similarity (retrieval closeness).
Similarity is never confidence. The ubiquitous-language document
adopts these words as the features land.

## Adopted, by version

### v0.6 additions (beside the 0004 scope)

- Retrieval provenance: every piece of answer evidence carries the
  retrieval method that found it (keyword, semantic, temporal,
  spatial, structured, hybrid) -- "why this evidence" becomes
  traceable, not just "which".
- A spatial filter joins the hybrid retrieval, arriving with
  personal place intelligence: a place condition in the question
  becomes a deterministic filter, the way time already does
  (ADR-0039).
- A golden retrieval dataset: queries with expected evidence,
  scored by recall and rank -- deterministic, model-free, and
  therefore in CI. Adding semantic machinery without measuring
  retrieval is not allowed.

### v0.7 additions (beside the 0005 scope)

- Structured model output, as an adapter concern: the Ollama
  adapter requests JSON-shaped output where a contract exists;
  validation is standard-library, not a new dependency.
- Evidence-contract validation past the schema: cited fact numbers
  must exist, claims must be supported by the cited evidence, time
  ranges must be consistent -- accept, reject or repair, and an
  unsupported claim is a defect even when the JSON parses.
- Prompt regression: prompts carry an id and a version beside the
  model name (the 0004 tracking, widened), and a golden evaluation
  (schema validity, citation accuracy, unknown-correctness) runs
  under the llm marker when a model or prompt changes, feeding
  `kiseki reread` and `kiseki compare`.

### v0.8 addition

- Cross-Timeline Analysis with drift detection: different evidence
  timelines (photograph activity, screen categories, journey
  frequency, hours of the day) compared on one axis, expressing
  before, after, during, overlap, co-occurrence, trend-aligned,
  divergent, unknown -- and never a causal claim: co-occurrence is
  reported as co-occurrence, with the absence of causal proof said
  aloud. Drift is baseline, then gradual, then persistent, then a
  new pattern; no judgement of better or worse. This feeds
  `suggest` its "why".

### v0.9 additions

- Provenance and dependency graphs: every derived artifact records
  its sources and versions, so a model, prompt or algorithm change
  can name exactly what needs recomputing -- and nothing else.
- Deletion semantics: removing evidence names how far the removal
  propagates (derived data, embeddings, profiles, insights); orphan
  derived data outliving its source is a defect.
- New evidence types enter the core only with a full definition:
  source, schema, privacy classification, provenance, timestamp and
  spatial semantics, retention, deletion, derived outputs,
  confidence, export policy.
- Privacy regression tests: the repository's promises checked in
  CI where checkable -- no raw coordinate served unasked, no
  network call introduced, no screenshot text stored, no personal
  data committed.

### v1.0 additions

- The security pass gets its checklist: loopback binding,
  authentication strategy, CORS, request limits, endpoint
  authorization, raw-coordinate protection.
- API DTOs are not domain entities: the served shapes are their own
  contract, free to stay stable while the domain moves.

## Declined, with the reason on record

- A vector extension (sqlite-vec and kin): the corpus is small and
  brute-force retrieval measurably fast. Held behind a trigger --
  when the golden dataset shows retrieval latency or quality
  failing at real corpus size, a VectorSearchPort with an optional,
  local-only adapter and an FTS fallback is the agreed shape.
- Multimodal (image) embedding: held until the meaning-space
  compatibility check the brief itself demands; revisit at v0.8.
- Pydantic, FastAPI, gRPC, a daemon-first design: declined outright
  -- the zero-dependency domain, the standard-library server and
  the incremental-before-daemon ladder all stand.
- New data sources for their own sake: KISEKI builds personal
  context from evidence; more sources are not more value.

## The goal, restated

The owner asks "which ramen place with the shrimp did I go to last
year?", "what changed since last year?", "is anything I have not
noticed?", "why do you think that?", "where next would be like me?"
-- and every answer walks question, retrieval, filter, derivation,
context, narration, with answer, why, evidence, confidence, time
range and limitations all traceable. The technology below that path
exists only to strengthen it.
