# Conformance kit

`kiseki-conformance` checks that a document conforms to one of the
contracts KISEKI publishes. It exists so that "any platform can feed this
library" is something you can run, not something you have to trust -- and
so that the one document KISEKI hands out can be held to the same standard.

| Contract | Direction | Checked because |
|---|---|---|
| [PhotoRecord v1](photo-record.md) | in | A producer needs to prove its output is acceptable without importing the library |
| [kiseki-interest-export v1](interest-export.md) | out | An input fails loudly at ingest; an output fails quietly, in somebody else's program |

## Command line

For producers written in Swift, Kotlin, or anything else:

```bash
kiseki-conformance output.json
```

The document is asked which contract it is (ADR-0081) -- `schema_version`
for a PhotoRecord, `schema` and `version` for an export -- so there is
usually nothing to say. `--contract photo-record` or `--contract
interest-export` says it outright; a document that names neither is
refused rather than guessed at.

| Exit code | Meaning |
|---|---|
| 0 | The document conforms |
| 1 | The document has violations, listed on stderr |
| 2 | The file could not be read or parsed |

The exit code makes it usable directly in a producer's own CI.

## Python suite

For producers written in Python, subclass the suite for your contract and
supply your output:

```python
import pytest
from kiseki_conformance import PhotoRecordConformance


class TestMyExporter(PhotoRecordConformance):
    @pytest.fixture
    def document(self):
        return my_exporter.export(sample_directory)
```

`InterestExportConformance` is the same for the export. Your producer does
not import the core library. It only produces JSON.

## What is checked

Structural rules come from the JSON Schema: required fields, value ranges,
patterns, the rule that `location_source` accompanies `location`, and the
rule that no exported topic names a place.

Semantic rules are checked separately, because a schema cannot express
them. JSON Schema 2020-12 has no way to compare two properties of the same
object, to require an order, or to make one part of a document agree with
another.

PhotoRecord:

| Check | Why it matters |
|---|---|
| Identifiers are unique | Identifiers are content hashes; duplicates mean the producer is not hashing content |
| Timestamps parse | A pattern match is not the same as a valid date |
| Timestamps carry an offset | Ordering across devices is impossible without one |
| `location_source` implies `location` | A source without coordinates is a producer bug |
| The document is not empty | An empty export is almost always a configuration mistake |

The interest export:

| Check | Why it matters |
|---|---|
| A topic appears once | Two readings of one topic leave a consumer to decide which to believe |
| `last_seen` is not before `first_seen` | The rule a schema cannot state |
| Months and days happened | `2026-13` matches the pattern and is not a month |
| Interests are strongest first | A consumer showing the first few must be shown the best few |
| Every staged topic is among the interests | The two halves of the document may not disagree (ADR-0069) |
| No topic names a place | Restated here in plain words, because it is the promise with a name (ADR-0047) |

An empty document means opposite things for the two contracts, which is
why the check is not shared: a PhotoRecord document with no records is a
misconfigured producer, and an export with no interests is a library that
has nothing to say yet.

## Adding a contract

Everything specific to one contract is a `Contract` value in
`contracts.py`: its name, how a document declares itself, its schema file,
and the rules a schema cannot express. Everything else -- loading,
validating, the CLI, the shared half of the pytest suite -- is the same for
all of them. A repository with a published contract of its own can copy the
package and replace that one value.

## Schema location

Each schema is published twice: at `schemas/` for discoverability, and
inside the package so that an installed copy is self-contained. A test
asserts each pair is identical, so they cannot drift. See ADR-0005.

Being inside the package is not the same as being inside the wheel, so
CI builds the wheel, installs it into an empty environment, and reads
both schemas and runs both suites from a directory outside the
repository (`tools/check_packaging.py`). This package exists to be
installed by somebody else; "installed without its schemas" is close to
the only way it can fail.
