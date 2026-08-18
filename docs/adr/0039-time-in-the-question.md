# ADR-0039: Time in the question



## Status

Accepted. Delivers proposals/0002, item 3.

## Context

Retrieval has carried a since/until window since ADR-0037, but
nothing filled it: "last year" in a question changed nothing, and
the evidence quietly skewed recent.

## Decision

A closed, deterministic list of Japanese and English time
expressions becomes the window: kyonen/sakunen (last year),
issakunen (the year before last), kotoshi (this year),
sengetsu/kongetsu, senshuu/konshuu, kinou/kyou, a bare N-gatsu
(the most recent such month), YYYY-nen, YYYY-nen M-gatsu, kyonen no
M-gatsu, koko/kono/kako/chokkin N days-weeks-months-years, and
saikin; in English: last/this year, month and week, yesterday,
today, a month name with a year, a bare year, last N units, and
recently/lately. "Recently" is ninety days, as a named constant.

No model reads the question: the same question and the same clock
always give the same window, and a unit test pins every entry. An
expression outside the list adds no window -- an unfiltered honest
answer beats a guessed filter. The clock must be timezone aware,
because the window is compared with timezone-aware observation
times.

Explicit time beats words: --since/--until on the command line and
since/until on /ask override anything the question says. The applied
window travels in the answer contract, so the owner can see what was
actually asked of the index.

## Consequences

- Last-year questions now answer from last year's evidence.
- The window is interpretation-free plumbing end to end; the place
  work (proposals/0002, item 4) is next.
