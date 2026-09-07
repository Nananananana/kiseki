# ADR-0093: One screen instead of six commands

## Status

Accepted. Closes #361. Follows ADR-0092, which decided what to say when
nobody asked a question; this decides what else belongs on the screen
that says it.

## Context

Forty-six commands. A person who wants to know how their year went runs
six of them and holds each result in the head while running the next.
Every one of the six is honest and narrow, which was right while the
derivations were being learned and is now the thing to fix: the parts
exist and nothing puts them together.

## Decision

**Four regions, each a derivation the library already has.**

```text
worth a look   what `today` chose, and why now      ADR-0092
what changed   the loudest movements between two kept readings
what is thin   the limits that bite, from the library's own counts
what is wrong  what `doctor` found
```

**It composes values, not text.** A screen that ran six commands and
pasted their output would be a worse `refresh`: six vocabularies, six
empty states, and no way to distinguish a region that is empty because
there is nothing to say from one that is empty because a source was
never read.

**Every empty region says which command would fill it.** The decision
`limits` made about naming absent sources (ADR-0088) and `ask` made
about a question it understood and cannot answer (ADR-0090), applied a
third time rather than invented. *Nothing to show* and *you have read no
notes* tell a reader different things, and only the second is
actionable.

**What is wrong comes from `doctor` itself, not from a second opinion.**
One list of faults, two renderings: `doctor` prints them among its
status lines and `now` prints them alone. A screen that computed its own
idea of wrong would drift from `doctor` on the first change to either,
and a reader would have no way to tell which was right. Only faults are
on the list -- a schema at the code's version and a profile with nothing
newer than it are states, not findings, and a screen reporting them
every day reports nothing.

**Trends are ranked by distance from their own baseline**, not by
strength. A topic that went from nothing to a little has moved further,
in the only sense a screen can mean, than one that was already strong
and stayed so. Steady topics are left out; three are shown, for the
reason ADR-0092 gives for three.

**It never reaches a model.** Every region is derived from what is
already stored. A `now` that called a model would be a screen that
mostly fails on a machine where the model is away, which is the state
v0.11 spent a version making legible rather than frightening
(ADR-0073). The model's work has its own commands, and `cost` says what
it would take before it is started.

## What it costs, measured

#361 asked for this rather than an assumption: six derivations at
once could be six times the work of one. It is not. Best of three
runs on a copy of the owner's library -- 4,950 photographs, 204
outings, 160 distinct places -- with the process floor (interpreter,
imports, path resolution) measured separately at 0.91s and
subtracted:

| command | wall clock | derivation |
| --- | --- | --- |
| `now` | 1.84s | 0.93s |
| `today` | 1.38s | 0.48s |
| `doctor` | 1.28s | 0.38s |
| `limits` | 1.00s | 0.10s |
| `trend` | 1.00s | 0.09s |
| `report` | 0.94s | 0.04s |
| the five, run separately | 5.61s | 1.08s |

The screen is **cheaper than its parts**: 0.93s of derivation
against 1.08s, because one connection, one report and one gazetteer
serve all four regions instead of five of each. Against the way a
person actually gets this today -- five commands, five process
starts -- it is 1.84s against 5.61s.

The incremental build's written trigger is not met and nothing here
is cached.

## It is not served, yet

`/today` is a route and `now` is not. Two of the four faults --
a missing gazetteer, a photograph with no reduced copy -- are
questions about the filesystem, and the server is deliberately not
given one (the same reason `/places` returns shapes and counts
while the command line names them). A `/now` whose *what is wrong*
were permanently empty would repeat exactly the defect this
decision fixes, so the route waits until the API's reach is
decided on its own terms rather than as a side effect of a screen.

## Consequences

- A derivation added later reaches the screen only by being chosen
  here, which is a decision rather than a default.
- `doctor` and `now` can no longer disagree about whether something is
  wrong, because there is one list.
- The floor is now half of it: 0.91s of `now`'s 1.84s is starting
  Python and resolving paths. That is the next thing worth
  measuring, and it is a packaging question rather than a
  derivation one.
