# WebRecord v1

> This describes a producer contract as it stands today. Nothing reads
> it yet: the producer and the core's reader are separate work. The
> contract is settled first on purpose, because a contract argued
> against working code is argued against sunk cost. Decisions are
> recorded in `docs/adr/`; proposed changes in `docs/proposals/`.

A fourth input contract, beside [PhotoRecord v1](photo-record.md),
[ActivityRecord v1](activity-record.md) and
[NoteRecord v1](note-record.md), and independent of all three. See
[the rules every contract shares](records.md).

A note is something the owner wrote. A page is something they opened,
which is a weaker signal and a stronger disclosure: weaker because
opening is not choosing, stronger because a browser holds every page
they did not mean to keep. This contract is shaped around that
asymmetry.

## The document

A JSON array of readings. **One record is one page on one day**, not
one visit. Forty visits to the same page in an afternoon are one
record; the same page opened again in November is a second, and the
returning is the signal (ADR-0076, as it is for notes).

```json
[
  { "owner": "me", "platform": "firefox", "day": "2026-08-29",
    "reference": "page:9f7630c78bfc0a41", "category": "reading",
    "labels": ["distributed systems", "raft"] },
  { "owner": "me", "platform": "youtube", "day": "2026-08-29",
    "reference": "page:1a2b3c4d5e6f7081", "category": "video",
    "labels": ["lathe", "metalwork"] },
  { "owner": "me", "platform": "firefox", "day": "2026-08-28",
    "reference": "page:c0ffee1234567890", "category": "health",
    "labels": [] }
]
```

| Field | Required | Meaning |
|---|---|---|
| `owner` | yes | Whose reading this is. |
| `platform` | yes | What produced it, for the owner's own reckoning. |
| `day` | yes | The day the page was open, `YYYY-MM-DD`, local. |
| `reference` | yes | A stable, opaque handle. A salted hash of the URL. |
| `category` | yes | One of the categories below. |
| `labels` | yes | Up to eight short labels, and empty for a category that carries none. |

Anything else in a record is ignored rather than refused.

## A video is a page

A watched video is this contract, with `platform` saying so. It is not
a contract of its own, and it does not carry a duration.

The temptation is real -- a video has a length, and length is
information a page has not. It is refused because a duration is a
**measure**, and this contract carries interpretations: a category and
some labels, each of which a person could argue with. Put minutes in a
record and the document stops being *what the owner attended to* and
becomes *how long they attended, per item, per day*, which is a
viewing history with a time budget attached. If this library ever
wants hours watched, it is a numeric contract like
[ActivityRecord](activity-record.md), and it can be argued for on its
own terms rather than smuggled in as a seventh field here.

## The categories

Carrying labels: `reading`, `study`, `work`, `project`, `reference`,
`recipe`, `travel`, `video`, `other`.

**Recorded and never labelled**: `health`, `money`, `people`,
`credential`, `shopping`, `news`, `private`.

The first five are NoteRecord's sensitive list, and they are sharper
here. A note about an illness is one somebody sat down to write; a
symptom typed into a search box at two in the morning is not
deliberate at all, and it is the most revealing thing in any browser
history. `people` covers a person's profile page for the same reason
it covers a note about somebody: they did not choose to be in this
library.

Two are new.

**`shopping`.** Purchases are declined as a source outright
(proposals/0008), and a product page is a purchase in another costume.
The count is evidence that the owner shops; the labels would be the
receipt.

**`news`.** This one is a deliberate loss. Labels on news reading
would be the most useful thing the web could give a profile -- and
they would be an inference about politics and religion, which this
library has no business making from what somebody read once. There is
no test that separates *follows seismology* from *reads one party's
paper*, and a library that cannot tell them apart should label
neither. The count stays, because how much news somebody reads is a
fact about their days.

And one is a catch-all.

**`private`.** Anything the classifier judges the owner would not read
aloud. Without it, everything unclassifiable lands in `other` and gets
labels, which is the failure this whole list exists to prevent. Its
count is still evidence -- that private browsing happens, which
surprises nobody -- and its labels never exist.

## What it deliberately does not carry

- **No URL.** Not a domain, not a path, not a query. This is the file
  name problem in its original costume, and worse: a URL is often the
  whole content.
- **No title.** A page title is a summary somebody else wrote of the
  thing the owner read, which makes it text about the reading and not
  about the record.
- **No text.** The producer reads and discards. A core that received
  the text and dropped it could not prove it had dropped it.
- **No site or host.** A list of the hosts somebody visits is the
  profile this contract exists not to carry.
- **No time of day.** A day is the unit, as it is for notes and
  activity. A browser knows the second; nobody needs it, and two in the
  morning is a fact about a person.
- **No visit count.** One page on one day is one record. How many times
  in that day is a measure, and the same argument as the duration.
- **No referrer, no tab, no window, no session.** How pages relate to
  one another is a graph of somebody's attention.

## The reference, and why a hash is not enough

The reference is a hash of the URL -- **salted, with a secret the
producer keeps and the core never sees.**

This is the one place where the web contract must be stronger than the
note contract, and the reason is not a matter of degree. A note's
reference hashes a path, and paths are private strings: to test
whether a hash belongs to `~/notes/diagnosis.md`, an attacker must
first guess that path. **URLs are public and enumerable.** Anybody
holding a records file and a list of URLs can hash the list and test
for membership, and the interesting lists -- clinics, forums,
political parties, dating sites -- are short and easy to write.

An unsalted hash of a URL is therefore not an opaque handle. It is the
URL, with an extra step.

The salt is generated once, kept by the producer beside the mapping it
already holds, and never travels with the records. The consequences
are the ones the owner wants: the core can still tell two readings of
the same page apart across months, and cannot say which page, and
neither can anybody who takes the file.

**A record file from one installation cannot be compared with another,
even for the same page.** That is correct. Two owners' histories are
not meant to line up.

## Producing one

The producer reads a browser profile the owner named, and a **window
of days the owner named**. Never "the whole history", never "every
profile on this machine". A source that recovers what somebody visited
three years ago and forgot is a search tool, and this is not one --
the same rule that keeps the notes producer out of the home directory.

**A page opened is not a page read.** The producer applies a minimum
dwell and discards anything below it: a redirect, a mis-click, a tab
opened and closed. Where the browser records a dwell, use it; where it
records only visit times, the gap to the next visit is the estimate.
The threshold belongs to the producer and is not in this contract,
because it depends on what the browser can say.

It classifies with a model, and where that model runs is the whole
privacy argument: the page's text reaches the classifier before
anything is discarded. The trust boundary (ADR-0073) applies exactly
as it does to captioning and to notes.

**A dry run comes first**, and is not optional for this source. A
misclassified photograph can be looked at again; a misclassified page
cannot, because the address is gone. `kiseki-web read` shows what it
would record -- a reference, a category and the labels, never an
address -- and writes only when told a second time with `--apply
--out`. `kiseki-web plan` comes before even that: it counts a window
without opening a page or reaching a model at all.

**The browser's database is locked while the browser runs.** The
producer copies it and reads the copy, and the copy is deleted
afterwards. It never writes to the original.

## Reading one

```bash
uv run kiseki web ~/kiseki-data/web-records.json
```

*(The producer writes that file today; nothing in the core reads it
yet. `kiseki web` is what the command will be called.)*

Re-reading a window is safe: a page whose day has not changed replaces
its reading, and the same page on a later day adds one.

What the core makes of a trail of them -- which subjects arrive
together, which were returned to, which faded -- is derivation, and
lives above this contract.

## The ten questions

`docs/records.md` asks ten of a new source. Answered in order, with the
sections above as the long form.

1. **Source.** A browser profile on the owner's own machine, exported
   by a producer outside this repository. Firefox `places.sqlite`,
   Chromium `History`; both are SQLite and both are locked while the
   browser runs.
2. **Schema.** Six fields, above. No URL, no title, no text, no host,
   no time, no count.
3. **Privacy classification.** The sharpest of the four contracts. A
   browser history holds symptoms, debts, other people, credentials,
   and every page the owner did not choose to remember. Answered by
   seven categories that carry no labels, by discarding the URL, by
   salting the reference, and by reading only a window the owner named.
4. **Provenance.** A derived statement points at `page:<hash>` and can
   say which day it came from. The mapping back to a URL lives with the
   producer, which is where the owner can ask.
5. **Timestamp semantics.** A day, in the owner's local time, from the
   browser's own record of the visit.
6. **Spatial semantics.** None. A page has no place, and the browser's
   guess at one is not the owner's.
7. **Retention.** As notes (ADR-0062): the readings are cheap to
   re-derive and the trail is what has value, so old readings thin by
   the same rules rather than by a rule of their own.
8. **Deletion.** `kiseki forget` removes a reading by reference, and
   what was derived from it goes with it (ADR-0061). Nothing outside
   the producer can name what was removed.
9. **Derived outputs.** Interests and themes, as notes do (ADR-0080),
   and with the same care: a word read often is not the same as a word
   lived. Never anchors -- a page is not a place -- and never trips.
10. **Export policy.** No. A web-derived interest may reach the
    interest export only through the ordinary gate (three readings and
    0.3 confidence, ADR-0069), and nothing that names the source, the
    reference or the category ever leaves.

## What this contract refuses to become

A record of everything the owner opened. The window, the dwell floor
and the seven unlabelled categories all pull the same way: this reads
what somebody paid attention to, and forgets the rest on purpose. A
producer that ignored all three would still emit valid documents, and
that is worth saying aloud -- **the contract cannot enforce the
window**. It is the producer's promise, checked by the dry run, and
the owner is the only one who can see whether it was kept.
