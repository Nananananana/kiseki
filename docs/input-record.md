# InputRecord v1

> This describes a producer contract as it stands today. Decisions are
> recorded in `docs/adr/`; proposed changes in `docs/proposals/`.

A fifth input contract, beside [PhotoRecord v1](photo-record.md),
[ActivityRecord v1](activity-record.md), [NoteRecord v1](note-record.md)
and [WebRecord v1](web-record.md), and independent of all of them. A
producer that emits photographs need not know this exists. They are
siblings: neither is a case of the other, and the core translates each
into its own vocabulary (ADR-0065).

A day has more than one face. Photographs say where somebody went,
notes say what they wrote, pages say what they read, steps say how far
they walked. This says **how long they were at the keys** — and
nothing else about it.

## The document

A JSON array of days. **One record is one calendar day.**

```json
[
  { "owner": "me", "platform": "kibi", "day": "2026-09-05",
    "active_minutes": 192, "events": 18060,
    "by_family": { "key": 14000, "button": 2100, "wheel": 900, "motion": 1060 },
    "apps": 2, "corrections": 41 },

  { "owner": "me", "platform": "kibi", "day": "2026-09-06",
    "active_minutes": 64, "events": 5120,
    "by_family": { "key": 4000, "button": 1120 }, "apps": 1 }
]
```

The second day carries no `corrections`. That is not an omission; see
below.

| Field | Required | Meaning |
|---|---|---|
| `owner` | yes | Whose day this is. One library, one owner. |
| `platform` | yes | What produced it, for the owner's own reckoning. |
| `day` | yes | A calendar day, `YYYY-MM-DD`, in the owner's local time. |
| `active_minutes` | yes | Minutes with input, `0`–`1440`. |
| `events` | yes | Input events counted that day. |
| `by_family` | no | Events split by kind — `key`, `button`, `wheel`, `motion`. Counts only. |
| `apps` | no | How many applications were touched. A count, never a name. |
| `corrections` | no | Backspaces and undos, **where the recorder could count them**. |
| `recorded_at` | no | When the producer wrote the record, for its own reckoning. |

Anything else in a record is ignored rather than refused.

## `corrections` absent is not `corrections: 0`

This is the one rule here worth reading twice, and it came from the
first producer.

A recorder reading a **redacted** or **structural** log knows that an
event happened and not which key it was. It therefore cannot tell a
correction from any other keystroke — not "there were none", but
"nobody could count". Reporting `0` there would turn the second into
the first, and a reader has no way back from that.

So the field is **optional**, absent means *unknown*, and the library
keeps the difference all the way to the column, which is nullable.
`kiseki input` says how many of the days it read could count:

```text
  days read     14
  days held     14
  corrections   counted on 9 of 14; the rest could not be counted,
                which is not none
```

A producer that can count sends the number. A producer that cannot
**omits the field** — it must not send `0`.

## What it does not carry

No key names. No words, and no text of any kind. No application names,
no window titles. No times of day — a day, not a timeline. No
position. No session identifiers, no durations of anything but the day
itself.

The reduction happens **in the producer**, on the owner's machine,
before a document exists. This library never sees what was discarded,
which is the point: a contract that carried the raw stream and
promised to forget it would be asking to be trusted, and this one has
nothing to be trusted about.

## What the core makes of it

A measure, and only a measure. It reaches `kiseki report`,
`kiseki privacy` and `kiseki limits` as a count of days, exactly as
`ActivityRecord`'s steps do.

**It never reaches the profile.** Fifteen thousand keystrokes is not a
topic and cannot become one. Whether a day at the keys should ever
inform an interest is a question that needs a corpus rather than an
argument, and the argument for pages (#350) is the shape it would have
to take. See ADR-0091.

## Reading one

```bash
uv run kiseki input ~/kiseki-data/input-records.json
```

Re-reading a day replaces it: a day is a state, not something returned
to, which is why this is keyed by day alone and unlike a note or a
page (ADR-0076).

**There is no `owner` column**, here or anywhere in the schema. One
library belongs to one owner. Several people on one machine means
several `KISEKI_DATA_ROOT`s, not an owner field in a table — see
`docs/cli.md` for what a data root holds.

## The ten questions

`docs/records.md` asks ten of a new source.

1. **Source.** A keyboard and pointer recorder on the owner's own
   machine, which reduces to counts before writing.
2. **Schema.** Eight fields, above. No names, no words, no times.
3. **Privacy classification.** Counts of physical actions. The
   sensitive thing about typing is *what* was typed, and none of it
   is here; the contract has nowhere to put a character.
4. **What it cannot say.** Which application, which document, which
   hour. Whether the person was working or playing. Whether a
   correction was a typo or a change of mind.
5. **Refusal.** A day beyond two million events, a negative count,
   `active_minutes` outside a day, or families summing past the day's
   own total.
6. **Absence.** A library with no InputRecord behaves exactly as it
   did before one existed (ADR-0063).
7. **Replacement.** Same day replaces.
8. **Ownership.** The owner's, on the owner's machine. Nothing
   leaves.
9. **Derivation.** Counts only, and no interest.
10. **Conformance.** `kiseki-conformance --contract input-record`.
