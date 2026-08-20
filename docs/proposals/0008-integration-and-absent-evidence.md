# Proposal 0008: Integration, and evidence that may be absent

Status: Accepted. Follows proposals/0007 after v0.9 shipped. It keeps
0007's v0.10 and v0.11 and adds to each; it plans v0.12 and v0.13,
which integrate rather than extend; and it fixes the rule that makes
several kinds of evidence safe to have: every source may be missing.

## The shape of the problem

Nine versions added surfaces. There are thirty-three commands, and a
reader who wants to know how their year went runs six of them. Each
one is honest and narrow, which was right while the derivations were
being learned, and is now the thing to fix: the parts exist, and
nothing puts them together.

At the same time the evidence is about to stop being one kind. Web
pages, watched videos and step counts are all defensible sources, and
each of them will be absent for most readers most of the time.

Those two facts point the same way. Integration is only safe if a
derivation can say what it read and work without the rest.

## The rule that makes the rest possible

**Sparse by construction.** Every derivation declares the evidence it
can use, works with any subset of it, and says which sources its
answer came from. Not "handles missing data gracefully" -- structurally
incapable of requiring a source.

Enforced rather than intended: a test matrix runs each derivation with
every source removed in turn, and a derivation that fails or lies
about its sources fails the build. This is how the library already
treats a model that is unavailable (ADR-0037: retrieval keeps the
words channel) and an absent gazetteer (places stay unnamed) -- raised
to a rule that covers every source, and stated before the sources
arrive.

## v0.10 -- More than photographs: the boundary

As proposals/0007 wrote it -- records as siblings with PhotoRecord v1
frozen, the new-source checklist as a gate, provenance and dependency
graphs, per-source counts in `privacy` and `doctor` -- plus:

1. Sparseness as a structure: `Evidence` names its source, every
   derivation declares which sources it can read, and the test matrix
   above lands with the boundary rather than after it.
2. Every answer names its sources. `ask`, `tell`, `insights` and
   `suggest` already cite evidence; they now say which kind of witness
   each piece was.

## v0.11 -- The first new sources

Web pages and watched videos as proposals/0007 wrote them -- read into
a category and labels, with the URL, the title and the text discarded
at ingest -- plus:

1. **Daily activity: steps, distance climbed, floors.** Chosen first
   among the numeric sources because it is the least sensitive thing a
   phone knows: a count per day, with no positions in it, exported by
   the owner from their own device. It proves the record contract can
   hold a number as well as a label, and it meets the existing
   derivations immediately -- a trip with twenty thousand steps a day
   was a different trip.
2. Both sources arrive through the v0.10 gate, and both are optional
   in the sense the rule demands: a library with neither behaves
   exactly as v0.9 did.

### Sources considered and declined, with the reason

- **Transit card history**: names where and when precisely, and reveals
  people the owner travelled with. A photograph is something they chose
  to take; a fare gate is not.
- **Purchases**: the same, plus financial detail the library has no
  business holding (ADR-0030's screen categories already refuse it).
- **Messages and mail**: other people's words, which are not the
  owner's to interpret.
- **Calendar titles**: the same in miniature. The *density* of a
  calendar -- how full a week was -- is defensible and may return in
  v0.13; the titles never are.
- **Sleep and heart rate**: medical in character. A step count is a
  count of steps; a heart rate is a symptom, and this library is not a
  place to interpret one.
- **Weather**: not a source at all. It is a provider, and the boundary
  for it already exists (ADR-0056): it may annotate a suggestion and
  may not create evidence.

### What landed early, and what waits for data

The receiving half of daily activity landed in v0.10 rather than
v0.11: `DailyActivity`, the `daily_activity` table, ActivityRecord v1
and `kiseki activity` all exist and were exercised on a hand-written
document. Building the contract before designing the shared rules was
the point -- `docs/records.md` is drawn from two real contracts rather
than from one and an imagination.

The producer that converts an Apple Health export into that document
waits for v0.12 or later, for the plainest of reasons: the owner has
not exported one yet, and a converter written against an imagined XML
would be a guess. Nothing else waits on it.

## v0.12 -- One question, the right machine
The integration begins where the reader is: with a question.

1. **Route the question.** "What did I eat in Seoul?" is a retrieval
   question. "Am I going out less than last year?" is not -- it is
   `compare` and `drift`, and answering it with a text search is how a
   library sounds confident and says nothing. A deterministic
   classifier sends a question to the derivation that can answer it,
   and the answer still cites evidence and still says "I don't know"
   when nothing supports one.
2. **`kiseki now`.** One screen for what the six commands say
   separately: what is worth a look, what changed, what to do next, and
   anything the doctor found. The thing a reader actually opens.
3. **Evidence from several kinds at once.** An answer may cite a
   photograph and a step count in the same breath, each labelled with
   what it is.

4. **Documents on the way out.** The answers are contracts too. Today
   `--json` returns whatever `payloads.py` happens to build; the
   interest export (ADR-0047) is the only shape with a name and a
   version. `AnswerDocument v1`, `ProfileDocument v1` and
   `SuggestionDocument v1` give the same treatment to what a caller
   actually reads: a document in `docs/`, a version, and a conformance
   test, so that a phone app, another visualisation or another AI can
   use KISEKI through a contract rather than through a prompt. The
   place to do it is here, because `kiseki now` is the first surface
   whose whole purpose is to be consumed by something else.
## v0.13 -- Your rhythm

The integration completed: not another derivation, but the one that
uses all of them.

1. **A typical week, and a typical month**, built from whatever sources
   exist -- outings, photographs, screens, steps, trips -- and stated
   with the arithmetic behind it.
2. **Departures named, never judged.** "This month is unlike your
   typical month in these ways" -- and the ways are numbers.
   Co-occurrence stays co-occurrence (ADR-0058); there is still no
   word for "because".
3. **The rhythm is where trips, places and drift meet.** A trip is a
   week that broke the pattern on purpose; a dormant place is a piece
   of the rhythm that stopped. These are the same subject seen from
   different sides, and v0.13 says so once instead of five times.

## v1.0 -- Public

Unchanged from proposals/0007: PyPI, a frozen public API, the hardened
conformance kit, a security pass over `serve`, API DTOs separate from
domain entities, versioned documentation. **v1.0 adds no new
intelligence.**

## Standing decisions, unchanged

- Phase 3 stays schema-only until v1.0 (ADR-0047).
- A phone app begins as a producer speaking the record contract.
- The incremental build and the vector extension each wait for their
  written trigger.
- Merging several devices waits for a second device.
- Every version reserves its last issue for what the previous
  version's data says.
