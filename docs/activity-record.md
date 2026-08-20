# ActivityRecord v1

> This describes a producer contract as it stands today. Decisions are
> recorded in `docs/adr/`; proposed changes in `docs/proposals/`.

A second input contract, beside [PhotoRecord v1](photo-record.md) and
independent of it. A producer that emits photographs need not know this
exists, and a producer that emits activity need not know about
photographs. They are siblings: neither is a case of the other, and the
core translates each into its own vocabulary (ADR-0065).

## The document

A JSON array of records. One record is one calendar day.

```json
[
  { "owner": "me", "platform": "ios", "day": "2026-08-18", "steps": 8421,
    "distance_m": 6180.4, "floors": 12 },
  { "owner": "me", "platform": "ios", "day": "2026-08-19", "steps": 3007 }
]
```

| Field | Required | Meaning |
|---|---|---|
| `owner` | yes | Whose day this is. One library, one owner. |
| `platform` | yes | What produced it, for the owner's own reckoning. |
| `day` | yes | A calendar day, `YYYY-MM-DD`, in the owner's local time. |
| `steps` | yes | Steps counted that day. |
| `distance_m` | no | Metres travelled on foot, if the device says. |
| `floors` | no | Flights climbed, if the device says. |

Anything else in a record is ignored rather than refused: a producer may
carry its own notes, and this contract will not argue with them.

## What it deliberately does not carry

- **No time of day.** A day is the unit. Hour-by-hour movement is a
  location trace wearing a step counter's clothes.
- **No positions.** Where the steps happened is what photographs are
  for, and the library already knows what it needs to know about place.
- **No heart rate, sleep, weight or workouts.** A step count is a count
  of steps; those are symptoms, and this library is not a place to
  interpret one (proposals/0008 declines them on the record).

## Producing one

The owner exports from their own device and converts. Apple Health
exports an XML archive; Google Fit and Health Connect export JSON. A
converter is a small program outside this repository -- the core never
reaches for a device, the same rule photographs live under.

A day the device did not record is simply absent. There is no zero-fill
and no interpolation: a missing day means nobody counted, which is not
the same as a day of no steps.

## Reading one

```bash
uv run kiseki activity ~/kiseki-data/activity-records.json
```

The same day given twice replaces rather than doubles, so a re-export
that overlaps is safe to read again.
