# kiseki-interest-export v1

> This describes a published contract as it stands today. Decisions are
> recorded in `docs/adr/`; proposed changes in `docs/proposals/`.

The only document KISEKI ever prepares for the world outside the
machine (ADR-0047). Everything else -- photographs, coordinates,
captions, readings, the profile itself -- stays where it was made.

It is the mirror image of [PhotoRecord v1](photo-record.md). That one
is an **input**: KISEKI is its only consumer, and a malformed record
fails loudly at ingest, in front of the person who produced it. This
one is an **output**, and an output fails quietly, months later, in
somebody else's program. That is why it has a schema and a conformance
suite of its own: `schemas/interest-export-v1.json` is the normative
definition, and this page explains the reasoning behind it.

## The document

```json
{
  "schema": "kiseki-interest-export",
  "version": 1,
  "exported_on": "2026-08-30",
  "interests": [
    { "topic": "ramen", "score": 0.82, "confidence": 0.7,
      "first_seen": "2024-11", "last_seen": "2026-08" }
  ],
  "stages": [{ "topic": "ramen", "stage": "stable" }]
}
```

| Field | Meaning |
|---|---|
| `schema` | The contract this document is. Read it first, refuse what you do not recognise. |
| `version` | `1`. Anything that does not fit this shape changes it by a visible bump. |
| `exported_on` | The day the export was made. A day, never a moment. |
| `interests` | The corrected profile's interests, strongest first. |
| `stages` | Lifecycle stages, only for topics the interests carried out with them. |

Each interest carries `topic`, `score`, `confidence`, `first_seen` and
`last_seen`. Score says how strongly the evidence points at the topic;
confidence says how far the evidence can be trusted to support that
reading at all. Both lie in `[0, 1]`, and the two are never collapsed
into one number.

A stage is one of `new`, `returned`, `growing`, `declining`, `dormant`,
`stable`.

## What it deliberately does not carry

- **No place, named or not.** A list of places is a movement history.
  A topic beginning `place:` never leaves, however often it is seen.
- **No evidence reference**, photo identifier, or identifier of any
  other kind. There is no field to put one in.
- **No exact time.** Months for an interest, a day for the export
  itself. A timestamp locates a person.
- **No coordinate, no screenshot word, no image.**
- **No topic seen fewer than three times**, or held with less than
  0.3 confidence (ADR-0069). Not a statement about what is private: a
  statement about what has been shown. Twice is a pair of occasions;
  three times is a habit of the evidence.

Exporting is a deliberate act -- a command with `--out`, and
deliberately not a served endpoint.

## The rules a schema cannot express

JSON Schema 2020-12 cannot compare two properties of the same object,
cannot say that a list is ordered, and cannot say that one part of a
document must agree with another. Three rules of this contract are
therefore checked by the [conformance kit](conformance.md) rather than
by the schema, and a consumer is entitled to rely on all three:

1. **`last_seen` is not before `first_seen`.**
2. **Interests are strongest first**, by score times confidence, ties
   broken by topic. A consumer that shows the first few is showing the
   best few.
3. **Every staged topic is among the interests.** The two halves of
   the document can never disagree (ADR-0069).

And two the schema does express, restated because they are the point:
every interest carries a `confidence`, and no topic names a place.

## Checking one

```bash
kiseki export --out interests.json
kiseki-conformance interests.json
```

**The document is UTF-8**, as JSON exchanged between systems must be
(RFC 8259 section 8.1), with or without a byte order mark. `--out`
writes the bytes; so does printing to a terminal or a pipe, which is
not what a shell would have chosen. `kiseki export > interests.json`
on a machine whose locale is not UTF-8 used to write the console's
encoding instead, and the file that landed read back correctly on the
machine that wrote it and nowhere else (#368). If you are producing
this document rather than consuming it, that is the mistake to avoid,
and `kiseki-conformance` names it in a sentence when it sees one.

A producer of this document written in Python can subclass the suite:

```python
from kiseki_conformance import InterestExportConformance


class TestMyExport(InterestExportConformance):
    @pytest.fixture
    def document(self):
        return json.loads(Path("interests.json").read_text())
```

## Why this is versioned, and one-way

Whatever a later version of KISEKI does with interests meeting other
interests, it fits through this schema or changes it by a visible
version bump. The library does not know, and must not know, who reads
the export (ADR-0047): the contract is a statement about the most that
may ever leave, not about a recipient. Knowing that consumers exist is
a fact; depending on one would be a defect.
