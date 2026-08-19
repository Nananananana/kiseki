# ADR-0059: The promises are checked by machine

## Status

Accepted. Delivers the privacy regression tests of proposals/0007, v0.9.

## Context

The README makes six privacy claims and the architecture makes three
more. Every one of them is enforced somewhere -- a type without a
text field, a blur applied by default, a hook that refuses images --
and until now nothing checked that the enforcement was still there.
A promise nobody tests is a promise waiting to be broken by a change
that meant no harm.

## Decision

One suite holds them, and each test fails if the promise fails:

- Nothing leaves the machine: `kiseki demo` -- which ingests, builds,
  reads and derives -- runs with the socket constructor replaced by
  one that raises. A future dependency that dials out fails here
  before it reaches anyone.
- A screen reading has nowhere to put the words: the dataclass field
  names are checked for text, body, content, words and ocr
  (ADR-0030).
- The export carries no identifier, no place and no exact time: the
  forbidden list of ADR-0047, run against a profile containing all
  three.
- The blur is about a kilometre, with the number in the test.
- The privacy report still names what is never stored.
- No personal data is committed: no database or image file under
  `packages/` or `tests/`, which the pre-commit hook also refuses --
  belt and braces, because a hook can be skipped.

## Consequences

- The privacy section of the README is now a specification rather
  than a description.
- v0.10 and v0.11 bring sources whose text is far more sensitive than
  a photograph's. The suite that will catch a mistake there exists
  before the sources do.
