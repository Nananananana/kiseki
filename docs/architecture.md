# Architecture

> This describes the current architecture. Decisions are recorded in
> `docs/adr/`; proposed changes in `docs/proposals/`.

## Layers

```mermaid
flowchart TB
    CLI["interfaces<br/>cli"] --> CFG["config<br/>paths"]
    CLI --> ADP["adapters<br/>sqlite, memory, exif"]
    CLI --> APP["application<br/>pipeline"]
    APP --> PORT["ports<br/>protocols"]
    APP --> DOM["domain<br/>entities and services"]
    ADP --> PORT
    PORT --> DOM
```

Dependencies point inward. The domain layer at the centre imports nothing from
the standard library beyond `dataclasses`, `datetime`, `math`, `enum`,
`hashlib`, `statistics` and the typing and collections protocols, and
nothing from outside it at all.

Four contracts in `.importlinter` enforce this, and run in CI:

| Contract | Rule |
|---|---|
| Layer dependency direction | interfaces above config above adapters above application above ports above domain |
| Domain purity | the domain imports no external library |
| Domain has no I/O | the domain imports no `pathlib`, `os`, `tomllib` or config |
| Ingest independence | the reference producer imports no core domain |

The last one is what makes the platform independence real rather than claimed.

## Packages

| Package | Contains | Depends on |
|---|---|---|
| `kiseki-core` | domain, application, ports, adapters, CLI | nothing at runtime |
| `kiseki-ingest` | EXIF reader, reference producer | Pillow |
| `kiseki-conformance` | contract test kit for producers | jsonschema |

Optional adapters ship as extras, so `pip install kiseki` pulls in nothing.

## The input boundary

```mermaid
flowchart LR
    A["iPhone"] --> P1["kiseki-ingest"]
    B["Android"] --> P2["a Kotlin producer"]
    C["a camera"] --> P3["anything that emits JSON"]
    P1 --> R["PhotoRecord v1"]
    P2 --> R
    P3 --> R
    R --> K["kiseki-core"]
```

The core reads one format and no files. Thumbnails are referenced by a relative
string, resolved through a port, so moving storage between drives is a
configuration change with no data migration.

See [ADR-0002](adr/0002-photorecord-as-the-only-input-contract.md).

## Data flow

```mermaid
flowchart LR
    IN["PhotoRecord<br/>document"] --> PH[("photos")]
    PH --> ST["extract_stops"]
    ST --> OA["assemble_outings"]
    ST --> AE["estimate_anchors"]
    OA --> OU[("outings")]
    AE --> AN[("anchors")]
    OU --> RD["readings<br/>captions, singles,<br/>screens, subjects"]
    PH --> RD
    RD --> PR["interests<br/>and profile"]
    AN --> PR
    PR --> IT["interpretation<br/>trend, lifecycle, insights,<br/>compare, discover, suggest"]
    RD --> IX["search index"]
    IX --> AS["ask"]
    PR --> AS
```

Readings accumulate and resume; interests and everything past them are
derived on demand, through the correction log. Nothing between
`readings` and `ask` is stored except the search index and the profiles
the owner chooses to keep.

Photographs accumulate. Outings and anchors are derived, and are replaced
wholesale on every rebuild rather than amended, because adding one photograph
can merge two outings or split a third.

See [ADR-0013](adr/0013-derived-data-is-replaced-not-amended.md).

## Testing

| Layer | What it covers | Runs in CI |
|---|---|---|
| unit | domain, config, application, CLI | yes, in seconds |
| contract | one suite applied to both the fake and the real adapter | yes |
| integration | anything calling a real model, marked `llm` | no |

The application layer is tested entirely against fakes: no database, no
filesystem, no model. That is why the ports exist.

Two suites exist to catch what unit tests cannot. The golden retrieval
dataset (`tests/golden/retrieval.json`) states, for fixed corpora, which
documents a question must return; it needs no model and runs in CI, and
it has already caught two ways a filtered question could be starved.
The answer check (ADR-0054) validates a model's reply against the
evidence it was given, so a prompt change that starts inventing
citations is visible.

## Decision records

Every non-obvious choice is written down in [adr/](adr/), including the ones
that were later reversed. ADR-0009 and ADR-0011 remain in the repository,
superseded by ADR-0012, because the reasoning that failed is as useful as the
reasoning that held.
