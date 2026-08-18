# ADR-0038: Ask, with the answer contract



## Status

Accepted. Completes hybrid search (proposals/0002, item 2).

## Context

The index (ADR-0036) and the retrieval (ADR-0037) can find the
evidence for a question; something has to phrase an answer without
gaining the power to invent one.

## Decision

`kiseki ask` retrieves first and phrases second. The retrieval
chooses the facts; the model receives them as a closed, numbered
list, must cite what it uses, and is told to say briefly when the
facts do not answer -- the narrative shape (ADR-0022). With no
evidence there is no model call at all.

The answer travels as a contract: answer text, a derived confidence,
the time range of the evidence, and the evidence itself. Confidence
is arithmetic over the retrieval -- strength (1.0 when the best
document led both channels) times coverage (evidence count,
saturating) -- so the model can never make an answer more certain
than the evidence is.

`/ask?q=...&lang=ja` serves the same contract as JSON over the local
API (ADR-0026): GET only, one fresh connection per question because
SQLite belongs to the thread that opened it. Evidence texts carry no
coordinates by construction (ADR-0036), and the model is instructed
never to mention any.

## Consequences

- `kiseki ask "..."` and `--json` land; `kiseki index` after each
  refresh keeps them current.
- Temporal retrieval (proposals/0002, item 3) will drive the
  since/until window the whole chain already carries.
