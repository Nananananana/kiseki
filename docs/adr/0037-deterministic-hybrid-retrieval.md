# ADR-0037: Deterministic hybrid retrieval



## Status

Accepted.

## Context

`kiseki ask` needs the best evidence for a question. The index
(ADR-0036) offers two views of the same documents: words (FTS5) and
meaning (vectors). Either alone fails predictably -- words miss a
Japanese question over English captions, meaning alone blurs exact
terms.

## Decision

Ask both channels to a fixed depth and merge by reciprocal rank
fusion (k = 60): a document's fused score is the sum of 1 / (k +
rank) over the channels that found it, ties broken by document key.
The fusion is arithmetic on ranks -- no weights to tune, no model in
the loop -- so the same index and question always give the same
answer, and a unit test can pin it.

Raw questions become FTS5 queries by tokenising and OR-joining
quoted words, so operators and punctuation stay inert and partial
matches still count. An unavailable embedder degrades retrieval to
the words channel instead of failing the question (ADR-0015 spirit);
a refused embedding propagates, as in indexing.

`since` and `until` bound the hits by observed time -- the hook the
temporal work (proposals/0002, item 3) will drive.

## Consequences

- Retrieval is a pure library layer: no CLI, no HTTP, no storage of
  its own; `kiseki ask` (part 3) composes it.
- Scores are comparable within one question only; the answer
  contract will derive confidence from them rather than expose them.
