# ADR-0054: An answer is checked past its schema



## Status

Accepted. Delivers the evidence-contract validation of
proposals/0006, assigned to v0.7.

## Context

The answer contract requires citations and forbids answering
without evidence (ADR-0038), and the retrieval that feeds it is
deterministic. What was never checked is whether the answer keeps
the contract it was given: a citation can point at a fact number
that does not exist, a claim can name a year no evidence saw, and a
fluent paragraph can cite nothing at all. Each of those parses.

## Decision

validate_answer reports three defects, deterministically and
without a model: the answer cites nothing; the answer cites a fact
that does not exist; the answer names a year the evidence never
saw. `kiseki ask` prints each defect beside the answer, so the
reader sees the doubt at the same moment as the claim.

The answer itself is never rewritten. Repairing a sentence would
put the library's words in the model's mouth, and dropping the
answer outright would hide how often this happens. The model said
what it said; the check says what is wrong with it -- the posture
corrections (ADR-0044) and the label stoplist (ADR-0053) already
take: store what was said, judge at reading time.

The check reads a grouped citation -- "[F1, F5]" -- as the two
citations it is. Real answers group; a check that called that
uncited would report a defect the answer does not have, and a check
that cries wolf is worse than no check.

## Consequences

- The owner can see an unsupported claim without reading the
  evidence themselves.
- v0.8 decides, from the observed rate of each defect, whether an
  uncited or falsely cited answer should be refused rather than
  reported -- a decision made with numbers instead of taste.
- Prompt regression (proposals/0006) can score a prompt by the
  defects its answers carry.
