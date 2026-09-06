# ADR-0091: A day at the keys is a measure, and absent is not zero

## Status

Accepted. Closes #412, after the owner accepted a fifth contract.
Follows ADR-0065, which said the record types are siblings, and
ADR-0010, which separates a measure from an interpretation.

## Context

A day has more than one face. Photographs say where somebody went,
notes say what they wrote, pages say what they read, steps say how
far they walked. Nothing said how long they were at the keys, and a
recorder that already produces that as counts existed.

## Decision

**A fifth input contract, and a measure only.** `InputRecord v1`
reaches `report`, `privacy` and `limits` as a count of days, exactly
where `ActivityRecord`'s steps reach, and **never the profile**.

That placement is not caution for its own sake. It is what the
evidence supports: fifteen thousand keystrokes is not a topic. The
measured fact behind the decision is that `ActivityRecord` has sat in
the same place since it was added and no derivation has wanted it
anywhere else. Whether a day at the keys should ever inform an
interest is a question for a corpus, and #350 is the shape that
argument has to take.

**Absent is not zero.** `corrections` is optional, and its absence
means the recorder could not count, not that there was nothing to
count. The first producer explained why: reading a redacted or
structural log, it knows an event happened and not which key it was,
so a correction is indistinguishable from any other keystroke.
Sending `0` there would turn *nobody could count* into *there were
none*, and no reader could tell afterwards.

So the field is nullable in the domain, nullable in the column, and
optional in the schema; `kiseki input` reports how many of the days
it read could count. A producer that cannot count **omits the
field** and must not send `0`.

This is the same distinction `limits` already draws between a
reading that came back empty and one withheld by category: two
numbers that look alike, mean opposite things, and were being added
together (#396).

**`owner` is required in the document and stored nowhere.** Every
input contract carries `owner` for the producer's own reckoning and
for a person reading the file; the core drops it. There is no owner
column in the schema, and there will not be: one library belongs to
one owner (`docs/records.md`), and several people on one machine
means several data roots. An earlier note of mine proposed keying
this table `(owner, day)`; that was wrong and would have quietly let
one library hold two people.

## Consequences

- Schema version 10. A library at 9 migrates by gaining an empty
  table; every derivation already survives a source holding nothing
  (ADR-0063).
- `limits` gains a sixth source, so a question about the owner's days
  can be told that none were read.
- The conformance kit gains a fifth contract. `ActivityRecord` still
  has none, which is now visible rather than merely true.
