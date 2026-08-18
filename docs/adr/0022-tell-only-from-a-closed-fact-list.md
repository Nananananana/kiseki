# 0022 Tell only from a closed fact list, and cite it



## Status

Accepted

## Context

A profile of numbers is honest but hard to recognise oneself in;
v0.2 promised prose. Prose from a language model invites the failure
this library was designed against: statements about a person that
nothing measured supports. The narrative stage needs the model's
words without the model's imagination.

## Decision

**The model receives a closed, numbered list of facts and nothing
else.** Measures first, then the strongest subject interests by score
times confidence, capped. The instruction forbids inventing details or
generalising beyond a fact, and requires each claim to cite its fact,
like [F3]. A reader can check every sentence against the list, and the
list against the stores.

**Coordinates stay silent.** Place interests are not given to the
model: a coordinate pair is not something a person recognises
themselves in. Places can join the narrative when they have names
worth saying.

**Nothing is stored.** A narration costs seconds and is derived
entirely from the profile and the measures, so it is regenerated on
demand. This is the one model stage without a progress store, because
there is no progress to keep.

**The prompt is tested; the generation is read.** Which facts, in what
order, in which language -- everything deterministic is pinned in CI
against the fake. The one real generation cannot be asserted on, so it
is verified by a person before merging, like any prose would be.

## Consequences

- `kiseki tell --lang ja` narrates the profile in Japanese; captions
  and subjects remain English facts underneath, as ADR-0020 planned.
- Citation quality depends on the model honouring the instruction; a
  narration that cites nothing is a visible failure, not a silent one.
- Recommendations ("what to do next weekend") are a different stage
  with different guardrails, and deliberately not this one.
