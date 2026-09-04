# The words this library uses

Twenty-six terms, each meaning one thing everywhere. A technical
review asked for the domain language to be fixed, and found that
nothing here wrote it down — so a reader met `stop`, `stay`, `outing`
and `anchor` in the same paragraph with nothing to separate them.

The point is not vocabulary for its own sake. **A word that means two
things is a bug waiting for the second reader**, and this library has
four layers that all talk about the same journey.

Every term below is checked against the code
(`tests/unit/test_the_words_this_library_uses.py`): a word defined
here that the code does not use is a word somebody removed, and a word
in this file is a word a contributor may rely on.

---

## What happened, from the evidence upward

These four are the spine, and they are the ones most often confused.

| word | what it is | what it is not |
|---|---|---|
| **stay** | the *behaviour*: being in one place for a while | not stored; the thing a stop represents |
| **stop** | one stay, as a record: some photographs, a time range, a centre | not a place — the same café visited twice is two stops |
| **outing** | a run of stops with no long silence between them | not a trip, not a route: it joins places and says nothing about how you travelled |
| **anchor** | somewhere returned to on enough separate days to be part of a life | never named. It is described by shares, not called *home* ([ADR-0040](adr/0040-an-offline-gazetteer-names-places.md)) |

**A place is not one of these.** `place:` is a reference to a
coordinate, and coordinates are private: they are blurred on anything
served or written, and the export carries none at all
([ADR-0047](adr/0047-export-is-a-one-way-abstraction.md)).

---

## What was in the frame

| word | what it is |
|---|---|
| **caption** | what a model said about one stay's photographs, or one photograph |
| **subject** | what a caption was found to be *about*: a handful of labels |
| **theme** | subjects gathered into a group that recurs |
| **reading** | one look at one thing on one day — a screenshot, a note, a page. Never the text itself; only a category and labels |

A **reading** is deliberately the same word for screens, notes and
pages, because they are the same shape: the producer read something,
kept a category and some labels, and discarded the rest.

---

## What it makes of you

| word | what it is |
|---|---|
| **interest** | a topic the evidence points at, with a score, a confidence and the evidence itself |
| **profile** | every interest at one moment, kept when asked for ([ADR-0070](adr/0070-reading-is-not-keeping.md)) |
| **trend** | how an interest moved between two halves of a period |
| **drift** | change measured across timelines, with no causal claim ([ADR-0049](adr/0049-mixed-evidence-is-stated-never-resolved.md)) |
| **lifecycle** | whether an interest is new, rising, enduring, dormant or gone |
| **insight** | a finding the library offers unprompted, with its evidence |
| **discovery** | something novel relative to what is usual for you |
| **suggestion** | somewhere to go back to or go next, with why now |

---

## What an answer rests on

This distinction is newer than the rest and is the one to read
carefully.

| word | what it is |
|---|---|
| **evidence** | the general term: anything an answer cites |
| **moment** | one retrieved thing — a caption, a note, a page. Cited `[F1]` |
| **pattern** | one derivation over all the data — a place's cadence, an interest, a trend. Cited `[G1]` |
| **grounding** | the patterns offered to an answer, each naming the command that produced it |
| **confidence** | how much the evidence supports the claim. Never the model's opinion — it is computed from the evidence and the model never touches it |

A moment says *this happened once*. A pattern says *this keeps
happening*. An answer that cannot tell you which it used is an answer
you cannot check, so `ask` prints both counts and the commands the
patterns came from.

---

## How things get in and out

| word | what it is |
|---|---|
| **contract** | a document shape with a name and a version, written down and checked ([docs/records.md](records.md)) |
| **producer** | a program outside this library that writes a contract. `kiseki-ingest`, `kiseki-notes`, `kiseki-web` are the ones shipped here |
| **derivation** | anything this library computes from what it stores. Every derivation declares what it can read, works without the rest, and says which sources its answer came from ([ADR-0063](adr/0063-evidence-names-its-source.md)) |
| **correction** | the owner saying a derivation is wrong. Stored beside it; nothing is rewritten |

---

## Two pairs worth keeping apart

**Measure and interpretation.** A measure counts and never explains
([ADR-0010](adr/0010-separate-measurement-from-interpretation.md)).
*Eleven visits over eighty-four days* is a measure. *You go there
often* is an interpretation. Everything above the measures interprets,
and cites.

**Reading and keeping.** Reading a profile computes one; keeping it
stores one. They were the same operation once, which meant every
derivation above was reading a record of how often somebody typed a
command ([ADR-0070](adr/0070-reading-is-not-keeping.md)).
