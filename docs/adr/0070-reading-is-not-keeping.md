# ADR-0070: Reading is not keeping

## Status

Accepted. Found by reading the history of a real library rather than
by any test.

## Context

`kiseki profile` kept a snapshot every time it ran. Printing the
profile to look at something else wrote a reading into the history:
fifty-three kept readings, twelve of them from three days, four from
one afternoon of debugging.

Every derivation that reads the history was reading a record of how
often somebody typed a command. The trend chose a baseline out of that
noise. Retention offered to thin forty-six readings, most of which
were the same day. "Seen 50" meant fifty invocations, not fifty
observations of an interest.

`Pipeline.profile` has taken `keep=False` since v0.2, for exactly this
reason -- the served GET uses it, because an HTTP read must change
nothing. The command did not.

No test caught it. The sparseness matrix, the privacy promises and the
demo all treat keeping as correct behaviour, because it was written
that way. It took looking at the list of kept readings and asking why
there were four from today.

## Decision

`kiseki profile` prints and keeps nothing. `--keep` keeps. `kiseki
refresh` passes `--keep`, because a weekly routine is the act that
should leave a mark, and printing is not.

## Consequences

- The kept history becomes a record of weeks rather than of
  keystrokes, which is what every derivation above it assumed.
- The existing history is still polluted: fifty-three readings, of
  which perhaps a dozen were deliberate. Retention can thin it
  (ADR-0062), and that is the owner's decision to make rather than a
  migration to run.
- A command that reads should be safe to run twice. That is worth
  stating as a rule and not only as a fix.
