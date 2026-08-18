# ADR-0036: A search index beside the stores



## Status

Accepted.

## Context

`kiseki ask` (proposals/0002, item 2) will answer questions from the
owner's own readings with evidence. That needs retrieval over the
stay captions, single captions and screen readings -- by words and by
meaning.

## Decision

Two tables in the same database, created by the search adapter itself
rather than by `connect()`: FTS5 is a build option of SQLite, and
only search should depend on it.

One document per answered reading -- `stay:<caption key>`,
`single:<photo id>`, `screen:<photo id>` -- carrying its text and the
time it was observed. Screen documents are the category plus the
labels; sensitive screens carry no labels (ADR-0030) and so never
reach the index. Withheld photographs (ADR-0032) are checked again
here, and no coordinate enters a document.

Documents are derived and synced deterministically on every run.
Vectors cost model time and are the resumable part, keyed by
(document, model) so a model swap re-embeds without losing the old
vectors; they are saved chunk by chunk, an unavailable model pauses
the run (ADR-0015), and a refusal -- for an embedder, a dimension
mismatch, which is configuration rather than weather -- propagates.

Vectors are packed floats brute-forced in Python: a few thousand
rows need no ANN library, and kiseki-core keeps its zero runtime
dependencies.

## Consequences

- `kiseki index` joins the model stages, resumable with `--limit`.
- Retrieval (part 2) and `kiseki ask` (part 3) read this index.
- Rebuilds never invalidate it: every key is content-derived.
