# ADR-0097: What a viewer can rely on

## Status

Accepted. Answers the orchestrator's R-G1 to R-G6, sent while there was
still nothing to draw, on the argument that they are cheaper before a
design than after. Follows ADR-0096, which put the graph behind a
command.

## Context

Sora asked for six things before Phase 4 exists. Four were already true
and two were not, and one of the two was a latent defect. The value was
not in the four.

## Decision

**Support and contradiction share one array, with `stance` as a
field.** There is nothing to contradict yet, which is exactly why now.
The argument is not about correctness but about which code is shorter:

> With two arrays, or two calls, the shorter code is the one that shows
> only the supporting half. Every consumer writes the shorter code
> eventually, and not from malice.

So `why --json` returns `evidence[]`, every entry carrying a `stance`,
and today every stance is `supports`. When contradiction arrives it
lands in the same array and no screen has to be changed to see it. A
test refuses a second array whose name contains *support* or
*contradict*.

This is the family's own shape a fourth time: tsumugi's `omissions[]`
the same size as `items[]`, akashi's `limits[]`, musubi's `null`
distinguished from `""`. What is missing must be as visible as what is
there.

**A label is written here, never copied.** Asked for as a declaration
of what a node's content may hold per privacy level; answered as a
property instead. **No label in the graph contains anything the owner
wrote, said or photographed.** Every one is composed from a *kind* --
*a note the library read* -- or a topic word a derivation already
published, or an opaque place name.

A consumer may therefore show a label without asking which privacy
level produced it. It is checked rather than promised: a test puts the
owner's own words into every field the builder touches and fails if any
of them reaches a node.

The line is drawn at the label and not the id. An id is an identifier
the producer already published, and a screen displaying raw ids would
be showing keys rather than content.

**Nothing in a drawing hint may mean anything.** `EdgeVisual` carried a
`dashed` flag meaning *offered rather than settled*. That is a fact
about the claim, not about the drawing, and Sora was right that a hint
which carries meaning is a second place the document says something --
after which one document draws two different pictures. It is gone;
nothing produced it yet, which is the cheapest moment to find such a
thing. What is left is size, grouping and a shorter label: **which of
several things to look at first**, never what any of them means.

**The document says which rules built it.** `built_by`, stored beside
the graph rather than stamped on at read time, because a graph read
back was built by whatever version was current *then*. Without it, a
finding that appeared because the owner did something new and one that
appeared because this library learned to look somewhere else are the
same news, and a screen would report a refactor as a life event.

**Every read is ordered.** The latent defect. SQLite happened to return
rows in rowid order and nothing promised it; a `VACUUM` is enough to
change that, and a consumer keyed on the hash of what we write would
read a reordering as *something happened today*.

## The test for that last one was green about nothing first

Worth recording, because it is the second time this month.

The first version read the document twice and compared, then vacuumed
and compared again. It passed with the `ORDER BY` removed — five nodes
written in id order come back in id order whether anything asked for it
or not. Reading twice and finding the same thing does not test a
promise about order; it tests that nothing changed in between.

The version that holds writes nodes named *zebra* through *vole* and
asserts the ids come back sorted. It fails the moment the clause goes.

## What is deliberately not answered yet

`diff` with a `withdrawn` list, which Sora argues is the screen only
this product can show. It belongs to Phase 5 and needs snapshots first.
Recorded rather than started, because the requirement is right and the
sequence is not negotiable: a diff of two graphs needs two graphs.

## Consequences

- Schema 12: one key-and-value table for what built the graph.
- A screen can be written against `why --json` today and will not need
  changing when hypotheses and contradiction arrive.
- The privacy question a viewer would otherwise have to ask per node
  does not arise, because the answer is the same for every node.
