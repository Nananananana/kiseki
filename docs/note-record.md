# NoteRecord v1

> This describes a producer contract as it stands today. Decisions are
> recorded in `docs/adr/`; proposed changes in `docs/proposals/`.

A third input contract, beside [PhotoRecord v1](photo-record.md) and
[ActivityRecord v1](activity-record.md), and independent of both. See
[the rules every contract shares](records.md).

A note is something the owner wrote, which makes it the most eloquent
thing this library reads and the most dangerous. The contract is
shaped so the dangerous part never arrives.

## The document

A JSON array of readings. **One record is one note on one day**, not
one note. A note the owner returns to across six months produces six
records, and the returning is the point: a thought had once and a
thought lived with look identical in a single record and nothing alike
in a trail of them (ADR-0076).

```json
[
  { "owner": "me", "platform": "obsidian", "day": "2026-08-29",
    "reference": "note:9f7630c78bfc", "category": "reading",
    "labels": ["distributed systems", "raft"] },
  { "owner": "me", "platform": "obsidian", "day": "2026-08-28",
    "reference": "note:1a2b3c4d5e6f", "category": "journal",
    "labels": [] }
]
```

| Field | Required | Meaning |
|---|---|---|
| `owner` | yes | Whose note this is. |
| `platform` | yes | What produced it, for the owner's own reckoning. |
| `day` | yes | The day the note was last written, `YYYY-MM-DD`, local. |
| `reference` | yes | A stable, opaque handle for the note. A hash of its path. |
| `category` | yes | One of the categories below. |
| `labels` | yes | Up to eight short labels, and empty for a sensitive category. |

Anything else in a record is ignored rather than refused.

## The categories

`note`, `reading`, `study`, `work`, `project`, `recipe`, `travel`,
`other` carry labels.

`journal`, `health`, `money`, `people`, `credential` are **recorded
and never labelled**. The count is evidence that the owner writes
diaries; the labels would be the diary. `people` is on that list
because a note about somebody is mostly about them, and they did not
choose to be in this library.

## What it deliberately does not carry

- **No text.** Not a summary, not a first line, not an excerpt. The
  producer reads and discards; the core has no field to put it in.
- **No file name.** `2026-resignation.md` says as much as its
  contents.
- **No path.** The reference is a hash of it, made by the producer,
  so the core can tell two readings apart without knowing what they
  are. The owner asks the producer, which holds that mapping.
- **No time of day.** A day is the unit, as it is for activity.
- **No folder structure.** Which folder a note sits in is a
  categorisation the owner made, and it names things: clients,
  people, projects.

## Producing one

The producer reads a folder the owner named -- never the home
directory, never "every text file on this machine". A source that
finds documents somebody forgot they had is a search tool, and this
is not one.

It classifies with a model, and where that model runs is the whole
privacy argument: the note's text reaches the classifier before
anything is discarded. The trust boundary (ADR-0073) applies to the
producer exactly as it applies to captioning.

**A dry run comes first.** A misclassified photograph can be looked at
again; a misclassified note cannot, because the text is gone. The
producer shows what it would record, and records only when told a
second time.

**The reference is relative to the folder you name, and the folder you
name is part of it.** The producer hashes each note's path relative to
its root, so a note keeps its reference when the whole folder moves --
and gets a new one if you name a different root next time. Reading
`~/vault` on Monday and `~/vault/notes` on Tuesday re-identifies every
note underneath, with nothing renamed. Measured: the same file under
two roots produces two references. Name the same folder each time, or
accept that the trail starts again.

**The day comes from the filesystem, and that is fragile.** A note
carries no date of its own; `mtime` is the only one there is. A `cp`
without `-p`, an unzip, or a converter that writes fresh files resets
every one of them, and the folder then produces one record per note on
the day of the copy -- internally consistent, and with every trail in
it gone. The dry run says so when more than half the notes share a
day, and refuses nothing: a folder written in one sitting looks the
same. Anything that prepares a folder for this producer must carry the
original `mtime` through.

## Reading one

```bash
uv run kiseki notes ~/kiseki-data/note-records.json
```

Re-reading a folder is safe: a note whose day has not changed replaces
its reading, and a note written again on a later day adds one.

What the core makes of a trail of them -- which notes were returned
to, which were written in one sitting, which subjects arrive together
-- is derivation, and lives above this contract.
