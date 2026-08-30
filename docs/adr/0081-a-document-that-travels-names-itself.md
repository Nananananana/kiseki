# ADR-0081: A document that travels names itself

## Status

Accepted. Settles a question raised while giving the interest export a
schema of its own (#302).

## Context

KISEKI's documents say what they are in three different ways, and a
third-party producer reading two of these contracts finds two
different answers to "what do I put at the top of the file":

```text
schema_version: "1.0"                          PhotoRecord: a version, no name
schema: "kiseki-interest-export", version: 1    the export: a name and a version
(no envelope at all)                            ActivityRecord, NoteRecord: an array
```

All of them implement the same discipline -- read the version first,
refuse what you do not recognise -- and they look like three
accidents. The obvious tidy-up is to align them on one form.

It was declined, for one bad reason and one good one. The bad reason:
`kiseki-interest-export` already has a consumer outside this
repository, which refuses any document whose `schema` and `version` do
not match, so aligning is a breaking change to somebody else's working
program in exchange for tidiness. That argument would evaporate the
day the consumer changed.

The good reason is that the three forms are not arbitrary. They differ
because the documents differ in one respect: whether the reader
already knows what it is holding.

## Decision

**A document that travels names itself. A document that is handed over
names its version.**

An input record is given to a command the owner chose -- `kiseki
ingest` wants PhotoRecord and nothing else. The reader knows what it
asked for, so the document only has to answer *which version*, and
`schema_version` is the whole of it. Where a contract's document is a
bare array, the command it was handed to is its name.

The interest export is written to a file and walks away. Its reader
may be a program nobody here has seen, reading it beside a dozen other
JSON files, months later. Nothing but the document itself can say what
it is, so it carries both halves: `schema` names the contract and
`version` says which one.

A later contract chooses by the same test, not by matching whichever
neighbour it resembles: outward-facing documents take the export's
shape, inputs take PhotoRecord's.

## Consequences

- The conformance kit can identify a document that names itself, and
  `kiseki-conformance` therefore needs no flag for PhotoRecord or for
  the export. A document that names neither is refused rather than
  guessed at.
- A contract whose document is a bare array cannot be identified that
  way. If one of those ever gets a conformance suite, it will need
  `--contract` to say which it is -- the cost of having no envelope,
  paid where it belongs rather than by every producer.
- `schema_version: "1.0"` stays a string and the export's `version`
  stays an integer. Neither is better; changing either breaks
  producers for no gain.
- The three forms stay three. Written down, they are a rule; undocumented,
  they were three accidents waiting to be tidied into a breaking change.
