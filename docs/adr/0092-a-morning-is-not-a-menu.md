# ADR-0092: A morning is not a menu

## Status

Accepted. Closes #411. Follows ADR-0090, which decided that a question
goes to the derivation that can answer it; this decides what to say when
nobody asked one.

## Context

A reader opened every morning needs a reason to be opened. The library
could already answer eleven questions, and answering eleven questions is
a menu: the person has to know which to ask before anything is worth
reading.

`suggest` was the closest thing and is not it. It ranks places by how
overdue they are and never asks whether anything *happened*. A topic
that stopped being dormant this week is the most interesting thing in
the library that day, and `suggest` has no idea it exists.

## Decision

**Three derivations, one fixed order, at most three items, each saying
why today.**

```text
overdue   a place past its own cadence          kiseki suggest
turned    a topic that came back from dormant   kiseki lifecycle
lately    an insight seen within the week       kiseki insights
```

**Nothing is derived here.** Every item is something a command already
says, chosen and given a reason, and each carries the command it came
from -- so a reader who disagrees with the choosing can see the whole of
it rather than being told to guess which command was spared them.

**The order between kinds is fixed and stated, not computed.** A
suggestion's confidence and an insight's confidence are different
numbers that happen to share a name and a range; ranking across them
would be arithmetic on incomparable things, which is the mistake
ADR-0064 documents for moments and this repeats for scores. Overdue
leads because a place unvisited for six hundred days is the loudest
thing the library can say.

**A topic appears once.** Something both returned and moving lately is
one card with the stronger reason, not two cards about one subject.

**Nothing to say is an answer.** An empty morning says so and names what
it looked for, rather than padding to three.

## The numbers are chosen, and are not settings

`AT_MOST = 3` and `RECENT_DAYS = 7` are guesses and say so. There is no
corpus of *what a person wanted to be shown today*, and writing one
would be this module's rules restated as evidence -- the argument
ADR-0090 made about routing, unchanged.

They are deliberately **not** `[derivation]` settings. A threshold the
owner can move is one the library must defend at every value; these two
decide how many cards a screen holds, which is the reader's business.
A reader wanting two takes the first two.

## Consequences

- The orchestrator's hero slot has a source, and `why_today` is a
  sentence it can print without rewriting.
- A derivation added later reaches the morning only by being chosen
  here, which is a decision rather than a default.
