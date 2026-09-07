# Proposal 0010: An evidence graph, and what it must not invent

Status: Proposed. Written against the owner's requirements document for
a Hypothesis Graph / Evidence Graph, after reading the current source
rather than the current documentation.

It agrees with the goal, disagrees with two of the mechanisms, and
reshapes the phasing around one observation: **most of Phase 1's
definition of done is already true, and the part that is genuinely new
is smaller and sharper than the document assumes.**

## What the goal is worth

The requirements document's closing sentence is the right one:

> a person's past, not as fixed memory, but as a hypothesis graph
> continuously updated by evidence

and the reason to want it is not the graph. It is that a reader can ask
*why did you conclude that* and be answered mechanically, from the
facts, without a model being asked to recall its own reasoning. This
library already refuses to answer what it cannot support (ADR-0015,
ADR-0090). It cannot yet **show its working**.

There is a second reason, and it is concrete: the orchestrator renders
what this library hands it. A list of interests is a list. A graph with
typed edges back to the days they came from is something a person can
look at and disbelieve in a specific place, which is the only kind of
trust worth having.

## Most of Phase 1 already exists, unnamed

Read against the source rather than the roadmap:

| the document asks for | what is already here |
| --- | --- |
| Fact / Observation, immutable | eight append-only tables of sourced readings; corrections are appended and applied at read, never overwritten (ADR-0044) |
| Interest with evidence | `Interest.evidence`, a tuple of `InterestEvidence(kind, reference, observed_at)` |
| Conclusion with evidence | `Insight` carries `evidence`, `derived_from`, `confidence`, `novelty`, and refuses to exist without naming what it was derived from |
| Snapshot | the kept readings in `profiles`. Keeping is a deliberate act, not a side effect of looking (ADR-0070) |
| Diff between snapshots | `kiseki compare` and `kiseki trend`, between two kept readings |
| Model proposes, algorithm decides | already the rule: the model never touches a confidence, and grounding facts come from derivations rather than recollection |
| Algorithm versioning | prompt versions are stored per reading; `kiseki reread` finds what an older version left behind (ADR-0087) |
| Rebuildable derived data | every derivation is recomputed from stored readings |

So the ordering the document proposes -- facts immutable, derived
things mutable, provenance kept -- is not a new principle here. It is
the existing one, written down as a graph.

**What is genuinely new is three things:**

1. **The edges are not stored.** Today a relationship lives in code: the
   merge order that lets a photograph outrank a note (ADR-0080), the
   append-only rule that lets a page add only what nothing else saw
   (ADR-0089). Those are relationships, and they are inspectable only
   by reading Python.
2. **There is no hypothesis object.** Nothing in the library holds a
   claim that is neither a measure nor a conclusion.
3. **Nothing can be traced backwards.** `Insight.evidence` is a tuple of
   strings inside a row. It is provenance that a person can read and a
   program cannot walk.

The first and third are worth doing on their own, and need no numbers
that do not exist. That is the reshaping this proposal argues for.

## Three things that will break it if built as written

### 1. The confidence arithmetic has no numbers to use

Section 7 shows a hypothesis moving `0.45 → +0.12 → +0.08 → −0.17 →
0.48`. The document says the calculation is decided at implementation
time, which is the right instinct, but the difficulty is not the
formula. It is that **the quantities being added are not comparable.**

Each derivation computes confidence by its own rule -- `days /
CONFIDENCE_FULL_DAYS` for notes, `len(sources) / CONFIDENCE_FULL_COUNT`
for screens, a sample-size confidence for anchors. Two interests both
scoring 0.6 from different sources are not equally well supported, and
nothing in the library says so (#390). Summing them into a hypothesis
confidence would give the incomparability a number and a decimal point,
which is how it stops being visible.

This is the mistake ADR-0064 records for moments and ADR-0092 repeats
for suggestion and insight scores. A third instance would be the one
that mattered, because everything downstream would rest on it.

**Recommendation.** Phase 1 stores support and contradiction as
**links and counts**, and computes no combined number. A hypothesis
that says *four facts support this, one contradicts it, here they are*
is honest, is renderable, and is what a reader actually wants to see.
The combined confidence waits for #390 to be decided, and inherits
whatever that decides rather than pre-empting it.

### 2. `confirmed` and `rejected` have no external validator

The status list includes `confirmed`. Confirmed against what? #365
records that no accuracy number exists for anything in this library,
because there is no labelled corpus and inventing one would be the
library's own rules restated as evidence.

A hypothesis that the library confirms from the same data that produced
it has not been confirmed. It has agreed with itself, and it will say so
with a status word that a reader will reasonably read as *verified*.

**Recommendation.** Two changes. Statuses describe the state of the
evidence rather than the truth of the claim -- `supported`,
`contested`, `unsupported`, `superseded` -- and the one status that
does claim truth, `confirmed`, is reachable **only through a
correction**, because the correction log is the only signal in this
library that comes from outside its own arithmetic. The owner saying
*yes, that is right* is ground truth; nothing else here is.

That also gives corrections a second job they are already shaped for:
they are appended, they are applied at read, and they already carry a
verdict.

### 3. Temporal decay is a threshold, and the library has a rule about those

Section 8 asks that older evidence weigh less. The instinct is right and
the number is the problem: any half-life is chosen, and this library
requires a chosen number to say that it was chosen (ADR-0006,
ADR-0087). A decay constant that arrives without that sentence will be
read as measured within a release or two.

**Recommendation.** Not in Phase 1. When it comes, it is a named
constant with the argument for its value in its own docstring, and it
is not a setting: a threshold the owner can move is one the library must
defend at every value.

## A fourth thing, from today

A graph handed to the orchestrator is **a document that leaves the
process**, and this week `kiseki report --json` was found writing the
owner's anchors -- the places returned to at night -- at full float
precision, because a default failed open and no test looked
(ADR-0095).

A place node must therefore carry no coordinate at all, which is what
grounding already decided for the facts that reach a prompt (ADR-0040):
a place is described by its cadence and its shares, never by where it
is. The graph is the second path with that exposure and it should be
born with the rule rather than have it added.

## The phasing this proposes instead

**Phase 1 -- the provenance graph.** Store the edges that already exist
implicitly. Every insight and every interest already names its evidence
and what it derived from; make that a table of typed edges rather than a
tuple of strings in a row, so a conclusion can be walked back to the
readings under it. No new numbers, no hypotheses, no arithmetic. The
test that matters: **every conclusion reaches a fact**, and a conclusion
that does not is refused rather than stored.

This alone answers *why did you conclude that*, and is the thing the
orchestrator can draw.

**Phase 2 -- hypotheses, without a combined confidence.** The object,
its statement, its status from the evidence-state list, and its links to
supporting and contradicting facts. Counts, not sums.

**Phase 3 -- correction as confirmation.** The owner's verdict reaches a
hypothesis. This is the phase that makes the graph mean something,
because it is the only phase that admits information from outside.

**Phase 4 -- merge and split, with their history.** Both are already
shaped by the existing merge order, which is where the rules for them
should come from rather than from new thresholds.

**Phase 5 -- snapshots and diff.** Partly here already: kept readings
are snapshots and `compare` is a diff. This extends them to the graph.

**Phase 6 -- the combined confidence, if #390 has been decided.** And
not before.

## What this proposal does not settle

- Whether the graph is stored beside the derivations or replaces them.
  It should be stored beside them first: a derived structure that
  nothing yet depends on can be deleted, and one that everything depends
  on cannot.
- What the tables look like. The document's list is a reasonable start,
  and the shape should follow the domain model rather than lead it.
- Whether the graph is served. It should not be, at first, for the same
  reason `kiseki now` is not: a route is a promise, and this one should
  be kept only once the shape has stopped moving.

## What it costs, and what to measure before believing it

The document targets tens of thousands of events and hundreds of
thousands of relationships. The owner's real library holds 4,950
photographs, 204 outings and 160 distinct places, so that target is an
order of magnitude beyond today and should be measured on generated
data rather than assumed.

One number is already known and is the one to watch: half of what
`kiseki now` costs is starting Python, not deriving anything (ADR-0093).
A graph that is walked once per command will disappear into that floor;
a graph that is rebuilt per command will not. The incremental update the
document asks for in section 34 is therefore the right instinct, and the
trigger for building it should be a measurement rather than the
expectation of one.
