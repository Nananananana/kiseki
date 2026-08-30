# Records, and the rules they share

> This describes the contracts as they stand today. Decisions are
> recorded in `docs/adr/`; proposed changes in `docs/proposals/`.

KISEKI reads records. It does not read devices, files on a phone, or
services on the internet: a producer outside this repository turns
those into a document, and the library reads the document. That is the
whole of the boundary, and it is why the core has no network code to
audit.

There is more than one contract now, and there will be more. They are
**siblings**: no record type is a case of another, none of them shares
a base schema, and the library translates each into its own vocabulary
inside the core.

```text
PhotoRecord v1    --+
ActivityRecord v1   |
NoteRecord v1       +--> Evidence --> Personal context
(a future one)    --+
```

| Contract | Document | Reads as |
|---|---|---|
| [PhotoRecord v1](photo-record.md) | `{"records": [...]}` | photographs, journeys, readings |
| [ActivityRecord v1](activity-record.md) | `[...]` | days of movement |
| [NoteRecord v1](note-record.md) | `[...]` | what the owner wrote, as category and labels |

A fourth is settled and unread: [WebRecord v1](web-record.md), for what
the owner opened rather than wrote. It is written before its producer
on purpose -- a contract argued against working code is argued against
sunk cost -- so it is not in the table above, which says what the
library reads today.

The documents are not even the same shape at the top level, and that
is allowed. A contract answers to its own subject, not to the contract
that came first.

These are the contracts KISEKI **reads**. The one it **writes** --
[kiseki-interest-export v1](interest-export.md) -- is a contract too,
and the only one anybody outside reads. It is not a record and answers
to none of the rules below; what it shares with them is the discipline
of naming its version and being checkable by the same kit. Which of
them names itself, and why they differ, is ADR-0081.

## What every contract must do

1. **Name the owner and the producer.** Every record carries `owner`
   and `platform`. One library belongs to one owner; the platform is
   for their own reckoning, never for behaviour.
2. **Ignore what it does not know.** An unrecognised field is passed
   over, never refused. A producer may carry its own notes, and a
   contract that argues with them forces every producer to be written
   twice. This is a rule about **the reader**, and
   the schemas are stricter than it on purpose: every object in every
   schema sets `additionalProperties: false`, because a producer that claims to
   emit PhotoRecord and emits PhotoRecord-plus-something is not
   emitting PhotoRecord, and the conformance kit exists to say so.
   Strict at the door, tolerant in the room -- the kit tells a producer
   its output is wrong, and the library still reads the document rather
   than losing a photograph over a note somebody left beside it.
3. **Speak the owner's local time.** Dates and times are the ones the
   owner lived, with an offset where a moment is meant and a plain
   date where a day is meant. The library compares them in one shape
   at the moment of comparison (ADR-0064) and stores what it was
   given.
4. **Survive a byte order mark.** Producers on Windows write one
   without being asked. Documents are read as `utf-8-sig`, which
   accepts a file with or without it.
5. **Land in a table of its own.** A new record type never adds
   columns to another type's table. If it turns out to be a mistake,
   the table is dropped and nothing else notices (ADR-0065).
6. **Be optional.** Every derivation works without it, and says which
   sources it read (ADR-0063). A library that has only photographs
   behaves exactly as it did before the contract existed.
7. **Say what it will not carry.** Each contract has a section naming
   what it deliberately leaves out, and why. That section is the
   privacy design; the rest is plumbing.

## The gate a new source passes

A new record type is not added until these are answered in its
contract document. The questions come from proposals/0006 and are
listed here because a checklist nobody can find is not a gate.

1. **Source.** Where does the data come from, and who exports it?
2. **Schema.** What exactly is in a record, field by field?
3. **Privacy classification.** What could this reveal that the owner
   would not choose to reveal? What is left out because of it?
4. **Provenance.** How does a derived statement point back to it?
5. **Timestamp semantics.** Is a record a moment or a day? Whose
   clock?
6. **Spatial semantics.** Does it carry a place? If not, say so.
7. **Retention.** What should a decade of it look like (ADR-0062)?
8. **Deletion.** What must disappear with it, and what survives it
   (ADR-0061)?
9. **Derived outputs.** Which derivations may read it, and what do
   they say differently because of it?
10. **Export policy.** May any of it leave in the interest export
    (ADR-0047)? The default is no.

A contract that cannot answer question three is not ready, whatever
else it can answer.

## Why the core reads documents rather than devices

Because a device is a moving target and a document is not. Apple
changes HealthKit, Google changes Health Connect, a phone changes its
photo library format; a producer absorbs all of that and the library
never notices. And because it makes the privacy promise checkable: a
library that cannot reach a device cannot leak from one, and the
matrix that proves no socket opens (ADR-0059) would be meaningless if
the core went looking for data itself.
