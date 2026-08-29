# ADR-0078: What the prompt says about people

## Status

Accepted. Measured against the corpus of ADR-0077, before and after.

## Context

The first measurement: twenty per cent of sensitive notes read as
ordinary, over-caution at zero. The classifier errs on the quiet side,
which is the direction nobody notices.

Both leaks mattered. A one-on-one about a colleague read as `work`
would have recorded his name, his workload and what he hoped for -- a
person who did not choose to be in this library, which is the whole
reason `people` is sensitive. A three-line diary about moving house
read as `other`.

## Decision

Two lines of guidance changed, and nothing else, so the measurement
would have one variable:

`people` is now named by a person appearing **with their
circumstances** -- their wishes, their family, their difficulties --
and says outright that a meeting note about a colleague is this rather
than `work`.

`journal` stopped leaning on feelings: a page about a day the writer
lived is a diary whether or not it says how anything felt.

And a general rule: when a note could be two things and one of them is
sensitive, choose the sensitive one.

The prompt version moved to `note/2`, so readings made under the older
guidance can be told apart and made again (ADR-0051).

## What it was worth

    leak rate      20.0% -> 10.0%    2 of 10 -> 1 of 10
    over-caution    0.0% ->  0.0%
    exact          15/24 -> 16/24
    labels leaked      7 ->      2

The `people` rewrite worked, and cost nothing: over-caution did not
move.

**The `journal` rewrite did not work.** The note it was written for is
still read as `other`. Reading it again, that note is a record of a
move rather than a page about a day, and `note` is a defensible
answer -- the guidance may be fine and the expectation may have been
too strict. It is recorded as unresolved rather than quietly dropped
from the corpus, because a corpus edited until it agrees measures
nothing.

## Consequences

- One leak remains, and it is named. A future prompt change has
  something to beat.
- Over-caution has been zero throughout. That is not comfort: it says
  the classifier under-warns, and a leak is silent while an
  over-warning is visible. If a later change trades some caution for a
  lower leak rate, the trade is worth making.
