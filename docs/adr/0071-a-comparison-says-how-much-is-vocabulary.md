# ADR-0071: A comparison says how much of itself is vocabulary

## Status

Accepted. Found by reading the first real trend, after ADR-0066 made
it short enough to read.

## Context

`kiseki trend` reported six hundred and fifty arrivals between the
fifteenth of August and the twenty-ninth. Almost none of them were new
interests. The reading of the fifteenth held a hundred and ninety
topics because the captions were still being written; the reading of
the twenty-ninth held six hundred and ninety-five because by then they
were done.

A comparison between two readings assumes they speak the same
language. Early in a library's life they do not, and the tool reported
the difference between two vocabularies as though it were a difference
in a person.

## Decision

Both listings print how many topics each reading held, and when the
two vocabularies overlap by less than eight tenths they say so:

    topics        190 then, 695 now
    98 of 787 topics appear in both readings; the rest is the
    vocabulary changing, not the interests

The threshold comes from the library itself. Across the first nine
days the overlap ran from 0.03 to 1.00, and the two pairs where the
readings had settled sat at 0.93 and 1.00 while every pair from the
days the model was still working sat at 0.73 or below. Growth alone
would not serve: one pair shrank to 0.38 of its size and still shared
only a third of its words.

The overlap is counted from the rows the listing shows, so the
sentence above the table can never disagree with the table.

Nothing is suppressed or reordered. The reader is told what they are
looking at, which is the posture of ADR-0058: the caution travels with
the comparison rather than being left for the reader to infer.

## Consequences

- A trend across a growing library reads as what it is.
- Once the readings settle -- one library-week, on this evidence --
  the line disappears on its own, because the overlap rises above the
  threshold.
