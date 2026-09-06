# ADR-0090: A question is routed without a model, and only ever narrowed

## Status

Accepted. Closes #360. Follows ADR-0039, which read *last year* out of a
question the same way, and #389, which gave `ask` the derivations to
choose between.

## Context

Two questions, one instrument:

```text
what did I eat in Seoul?             a moment. Retrieval answers it well
am I going out less than last year?  a rhythm. Retrieval searched captions
                                     for those words and cited what it found
```

The second is the dangerous failure, because it does not look like one.
#389 fixed half of it by offering every derivation's facts to every
question. That was right and it left the reader unable to tell which
kind of fact an answer rested on, and left *every* question paying for
*every* derivation's grounding.

## Decision

**A deterministic classifier, before retrieval.** Literal phrases in
both languages, in one table (`domain/services/question_routing.py`).
A router that asked a model which derivation to use would make the
route depend on whether the model is reachable -- after a version spent
making that answerable (ADR-0073) -- and would route a question by the
judgement of the thing being routed to.

**It narrows and never widens.** A routed question is offered the kinds
of fact it is about instead of all four. A question matching nothing
gets exactly what it got before this ADR: everything, and retrieval
decides. So the router cannot make an answer worse than the one before
it; it can only fail to improve one.

**Several kinds is not a conflict.** *Am I going out less than last
year* is rhythm and trend, and takes both. Nothing here picks a winner,
because nothing here knows enough to.

**Routed-to-nothing-held is named, not silent.** A question understood
as being about trends, on a library with no trend derived, says so and
names the command that would derive one. That is the honest form of
*fits none*: the question was understood and the answer does not exist
yet, which is a different thing from not being understood, and the
reader can act on exactly one of them.

**The route is printed.** An answer that came from the rhythm and does
not say so is worse than one the reader asked for by typing `report`,
because then they knew. `ask` prints what it read the question as, the
phrases that said so, and -- through those -- the command the reader
would have typed. A misroute costs a glance.

## What this is checked against, and what it is not

**There is no dataset of questions to derivations, and none was
written.** One written from imagination would be this module's own
rules restated as evidence -- the router specified by its author, then
graded against that specification. The retrieval golden set (v0.6) was
possible because a retrieved document is right or wrong about a
question independently of how retrieval works; a route is not.

So what is held instead:

- every phrase in the table routes as the table says, and the table is
  short enough to read whole;
- the four questions in `application/grounding`'s docstring -- the ones
  measured on a real library, before any of this -- route as that
  docstring says they should;
- narrowing never empties: a routed question whose kinds hold no facts
  keeps the facts it had rather than losing them;
- an unrouted question is offered exactly what it was offered before.

The vocabulary is **chosen**, like `min_page_days` and unlike
`SETTLED_SHARE`. When there is a corpus of real questions -- which is
what an orchestrator with a search box would produce -- the phrases are
the thing to measure and move.

## Consequences

- `kiseki now` (#361) has something to be a surface over: a routed
  answer rather than a menu of commands.
- A question about a derivation nobody has run yet gets told which one,
  which is the first time `ask` has been able to say that.
- Adding a derivation means adding its phrases here, or its facts are
  never selected for. That is a real cost and it is visible: the table
  and `grounding.KINDS` are held equal by a test.
