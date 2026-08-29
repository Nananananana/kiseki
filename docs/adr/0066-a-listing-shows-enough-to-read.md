# ADR-0066: A listing shows enough to read, and says what it kept back

## Status

Accepted. Found by the first run of the history commands against two
years of real photographs.

## Context

The history features waited fourteen days for a second kept profile
and then answered: `trend` printed five hundred rows, `insights` six
hundred, `lifecycle` five hundred, `compare` six hundred. Every row
was correct and the answer was unreadable. Only `discover`, which has
always capped its feed at ten, could be read at all.

An unbounded listing is not honesty. It is the appearance of honesty
with the work of reading left to somebody else.

## Decision

Every listing shows twenty rows by default, and says how many it kept
back: "showing 20 of 512; --all for the rest". `--limit` chooses a
different number, `--all` shows everything, and `--json` is never
truncated, because a program is not a reader.

The lifecycle caps per stage rather than overall: a hundred new topics
would otherwise fill the page and the dormant ones -- the ones worth
seeing -- would never appear.

Nothing is hidden without saying so. That is the difference between a
summary and a truncation.

## Consequences

- The history commands can be read, which is the first requirement of
  being useful.
- The ordering already in place decides what earns the twenty rows,
  so the cap is a display decision and not a judgement.
