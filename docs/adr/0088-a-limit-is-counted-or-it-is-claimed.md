# ADR-0088: A limit is counted, or it is claimed, and never both

## Status

Accepted. Decided while building `kiseki limits` (#364).

## Context

`kiseki privacy` used to *assert* that nothing left the machine. In
v0.11 it was rewritten to *compute* what leaves from the settings in
force (ADR-0074), and the day it stopped being a promise and became a
report, it was found to have been wrong for years — captioning had
been putting a reduced copy of a photograph into an HTTP body since it
was written.

`limits` applies that treatment to the reach of an answer rather than
to the flow of data. The argument in
[proposals/0009](../proposals/0009-what-the-owner-writes.md) is that a
tool trusted past its reach is worse than no tool, because the
behaviour it licenses is riskier than the behaviour it replaced.

Building it raised a problem the proposal names and does not solve.
Some of what it wants to say cannot be counted:

- *A profile built from nine days of readings cannot speak about two
  years.* Countable — the span is on disk.
- *A comparison whose vocabularies overlap by a third is about words
  rather than about a person.* Countable, and already counted
  ([ADR-0071](0071-a-comparison-says-how-much-is-vocabulary.md)).
- *An interest that appears in no photograph is invisible here, and
  the library has no way to know it is missing.* **Not countable, and
  the sharpest of the three.**

A report that mixes the two kinds without saying so is the failure
this command exists to prevent. A reader shown *you have no notes* and
*the library cannot see an interest you never photographed* in one
list will take both for measurements, and only one of them is.

## Decision

**No threshold is invented for this command.** Every computed limit is
a zero, a stated span, or `SETTLED_SHARE` — the 0.8 that ADR-0071
earned across nine days of real readings, where settled pairs sat at
0.93 and 1.00 and unsettled ones at 0.73 and below. No corpus exists
yet to earn another (#309).

The consequence is deliberate and uncomfortable: **a count that is
small but not zero is printed and not judged.** The command will not
say four notes are too few, because the number that made that sentence
true would have been chosen by its author to make it true, which is
the kind of sentence `limits` exists to replace. That is
[ADR-0010](0010-separate-measurement-from-interpretation.md) applied
where the temptation to interpret is strongest.

**The two kinds of limit live in different layers.** What can be
counted is computed in `application/limits.py`. What can only be
asserted sits in `interfaces/claims.py` beside `NEVER_STORED`, where
every line already carries the name of the test that fails if it stops
being true. The split is structural rather than editorial, so neither
list can quietly absorb the other: a limit that becomes computable
moves out of the claimed tuple, and one that cannot be computed can
never be smuggled into a report as though it had been measured.

The printed report keeps them under separate headings, and the
document keeps them under separate keys.

**The unseeable are printed even when nothing else bites.** A section
that appears only on a poor library teaches the reader that a quiet
report means no limits, and those three are always in force.

## What this makes checkable

The claim *the library cannot know what it is missing* is not a mood.
It rests on a property that can be tested: a source wired and empty
produces exactly the same report as a source that was never wired at
all. The library has one word for *you kept no notes* and *this
installation has no notes repository*, and cannot tell them apart —
so it can never say how much is missing, because it does not know the
denominator.

`test_nothing_here_claims_to_know_what_is_missing` holds that. If
somebody later teaches `limits` to look at the disk and report notes
it was never given, the test goes red, and that claim should leave the
asserted list and be computed instead. **That is the intended way for
this ADR to be superseded in part.**

## Consequences

- `limits` finds nothing on a full, settled library, and says so.
  Manufacturing a limit to look thorough would be the same failure as
  refusing to answer a question the library holds the answer to.
- Naming absent sources is a disclosure. It is the same disclosure
  `privacy` has printed from the same counts since v0.11, and a limits
  report that will not say which source is missing cannot do its job.
- `claims.py` gained the check it always described. Its existing test
  asserted only that a claim's test name began with `tests/`, so a
  claim could have pointed at a file nobody wrote. All six existing
  claims did resolve; nothing was keeping them that way.
- The report is a command and not yet a section carried by every
  answer. The proposal argues for the second, and it belongs after the
  grounding work in #390 rather than stacked on top of it.
