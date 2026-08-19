# ADR-0063: Evidence names its source, and any source may be absent

## Status

Accepted. Delivers the sparseness rule of proposals/0008, v0.10.

## Context

Nine versions read one kind of record, so nothing ever had to say
which kind. The next two add web pages, watched videos and daily step
counts, and every one of those will be absent for most readers most of
the time. A library with photographs and nothing else must behave
exactly as it does today.

That is easy to intend and hard to keep. Any derivation may quietly
come to require a source -- an index built before a search, a screen
reading assumed to exist -- and nothing would notice until somebody's
library lacked it.

## Decision

Sources are named in one enum, so adding a kind of witness is a line
rather than a search. Reserved names for the sources v0.11 brings are
written beside it.

The rule is enforced by a matrix rather than remembered: a library is
seeded with every kind of evidence, one kind is removed, and every
deterministic command runs against what is left. A command that
crashes, or that fails because a source it does not need is missing,
fails the build. Seven omissions -- including "nothing", which checks
the seeding itself -- against eighteen commands.

This is the treatment the library already gives an unavailable model
(ADR-0037) and an absent gazetteer (ADR-0040), stated once and applied
everywhere.

## Consequences

- A derivation cannot come to depend on a source without the matrix
  saying so, which is what makes v0.11 safe to attempt.
- The matrix is also an audit of what exists: it asks, for the first
  time, whether `suggest` works without captions and whether `profile`
  works without screens.
- Answers naming the sources they read is the next step, and the enum
  is what they will name.
