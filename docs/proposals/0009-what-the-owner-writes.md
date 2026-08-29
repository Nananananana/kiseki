# Proposal 0009: What the owner writes, and where the model is

Status: Accepted. Follows proposals/0008, written after the first
history commands ran against two years of real photographs and after
reading a sister project. It keeps 0008's shape and changes three
things: it adds the sources the owner writes rather than takes, it
puts the model's location before everything else, and it adds the
commands that say what the library cannot do.

## What the real data changed

The kept readings reached a fortnight apart on the twenty-seventh of
August and the history features answered for the first time. Ten
changes came out of one afternoon of reading their output, and two of
them were not features:

`kiseki profile` kept a snapshot every time it printed one. Reading
the profile wrote to the history, so every derivation above it was
reading a record of how often somebody typed a command (ADR-0070). No
test caught it. The sparseness matrix, the privacy promises and the
demo all treat keeping as correct behaviour, because it was written
that way.

`kiseki privacy` said that no network call exists, which stopped being
true the day captioning was written (ADR-0074). A reduced copy of a
photograph travels to the model in an HTTP body. It went to localhost,
so the outcome was right while the mechanism was described wrongly.

Both were found by a person reading output, not by a machine checking
it. That is worth stating in a plan: the matrix and the promises
catch what they were pointed at, and pointing them is still work.

## The rule that stands above the rest

**Sparse by construction**, unchanged from 0008. Every derivation
declares the evidence it can use, works with any subset, and names the
sources its answer came from. The matrix removes each source in turn
and fails the build if anything requires one.

## v0.11 -- Where the model is, and what the owner writes

1. **The trust boundary.** Landed (ADR-0073, ADR-0074). The model may
   be on another machine, the boundary is `same_host` by default, a
   host the owner names is admitted, and `kiseki privacy` computes
   what leaves rather than asserting it. Everything below inherits
   this: a source whose producer runs a classifier is only as private
   as the machine that classifier runs on.
2. **Notes: what the owner writes.** A folder of `.md` and `.txt`
   files, read by a producer outside the core, which classifies them
   locally and keeps only the category and the labels. See below.
3. **Web pages and watched videos**, as 0008 wrote them, and by the
   same shape as notes: the producer reads, the producer discards, the
   core never holds the text.
4. **A dry run before anything is recorded.** A producer that throws
   away the text is a producer whose work cannot be checked
   afterwards. It shows what it would record, and records only when
   told again.
5. **The name of a place.** `kiseki places` folds sixteen places into
   one town and says so (ADR-0072); a gazetteer that answered nearer
   would fold fewer, and the entries exist. The naming is the coarse
   part, not the clustering.

### Notes before the web

Notes come first, and not because they are more valuable. Reading a
folder of text files is simpler than reading a browser's locked
SQLite, so the contract can be settled against the easy source and the
hard one inherits a shape that has already been used -- the reason
daily activity came before the shared record rules in v0.10, and the
reason those rules are drawn from two real contracts instead of one
and an imagination.

They may also be the most eloquent source this library will hold. A
photograph is something the owner pointed a camera at; a page in a
browser history is something they happened to open. A note is
something they wrote. And it reaches where photographs cannot: the
profile says `python` because a screen was photographed, and says
nothing about what the owner was thinking while typing.

### What a note contract must refuse

Question three of `docs/records.md` -- what could this reveal that the
owner would not choose to reveal -- has the sharpest answer yet. A
notes folder holds diaries, other people's confidences, passwords, a
resignation letter, a diagnosis. So:

- **The text never reaches the core.** The producer classifies and
  discards, exactly as the web producer will. A core that read the
  text and then dropped it could not prove it had dropped it; a core
  that never receives it has nothing to prove.
- **The file name is discarded too.** `2026-resignation.md` says as
  much as its contents. This is the URL problem in another costume.
- **The reference is a hash of the path.** The core knows that two
  readings came from the same note and cannot know which note. The
  owner can ask the producer, which is where the mapping lives -- the
  same division photographs already have between a content hash here
  and a reduced copy there.
- **The dry run is not optional for this source.** A misclassified
  photograph can be looked at again. A misclassified note cannot,
  because the text is gone.

## v0.12 -- One question, the right machine

As 0008 wrote it -- questions routed to the derivation that can answer
them, `kiseki now` in place of six commands, evidence from several
kinds of witness at once, and documents on the way out
(`AnswerDocument v1` and its kin) -- plus:

**`kiseki limits`.** What this library cannot tell you, computed from
your own data rather than recited. A profile built from nine days of
readings cannot speak about two years. A comparison whose vocabularies
overlap by a third is about words rather than about a person
(ADR-0071). An interest that appears in no photograph is invisible
here, and the library has no way to know it is missing.

A tool trusted past its reach is worse than no tool, because the
behaviour it licenses is riskier than the behaviour it replaced. The
report says what it cannot see, from this installation's numbers.

## v0.13 -- Your rhythm

As 0008 wrote it: a typical week and a typical month from whatever
sources exist, departures named and never judged, and the place where
trips, places and drift turn out to be one subject. Plus:

**`kiseki eval`.** What the model tier is actually worth, measured
rather than asserted. Captioning is `qwen3-vl:8b` because it fitted;
nobody has asked what a larger model changes about the profile, or
whether a smaller one changes anything at all. The answer may be that
it is not worth the hours, and publishing that is more useful than
implying otherwise.

## v1.0 -- Public

Unchanged: PyPI, a frozen public API, the hardened conformance kit, a
security pass over `serve`, API DTOs separate from domain entities,
versioned documentation. **v1.0 adds no new intelligence.** Plus a
Japanese README, because the owner is Japanese and the first person to
read this in their own language should not be the last.

## Standing decisions, unchanged

- Phase 3 stays schema-only until v1.0 (ADR-0047).
- A phone app begins as a producer speaking a record contract.
- The incremental build and the vector extension each wait for their
  written trigger.
- Merging several devices waits for a second device.
- The Apple Health converter waits for an export to exist; the
  receiving half is done.
- Every version reserves its last issue for what the previous
  version's data says.

## Declined, with the reason

Unchanged from 0008 -- transit cards, purchases, messages, calendar
titles, sleep and heart rate -- and one addition:

**A notes folder the owner has not chosen.** The producer reads a
folder that was named for it, and never the home directory, never
"every text file on this machine". A source that finds documents the
owner forgot they had is a search tool, and this is not one.
