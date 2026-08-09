# Conformance kit

`kiseki-conformance` checks that a document conforms to the PhotoRecord v1
contract. It exists so that "any platform can feed this library" is something
you can run, not something you have to trust.

## Command line

For producers written in Swift, Kotlin, or anything else:

```bash
kiseki-conformance output.json
```

| Exit code | Meaning |
|---|---|
| 0 | The document conforms |
| 1 | The document has violations, listed on stderr |
| 2 | The file could not be read or parsed |

The exit code makes it usable directly in a producer's own CI.

## Python suite

For producers written in Python, subclass the suite and supply your output:

```python
import pytest
from kiseki_conformance import PhotoRecordConformance


class TestMyExporter(PhotoRecordConformance):
    @pytest.fixture
    def document(self):
        return my_exporter.export(sample_directory)
```

Your producer does not import the core library. It only produces JSON.

## What is checked

Structural rules come from the JSON Schema: required fields, value ranges,
patterns, and the rule that `location_source` accompanies `location`.

Semantic rules are checked separately, because a schema cannot express them:

| Check | Why it matters |
|---|---|
| Identifiers are unique | Identifiers are content hashes; duplicates mean the producer is not hashing content |
| Timestamps parse | A pattern match is not the same as a valid date |
| Timestamps carry an offset | Ordering across devices is impossible without one |
| `location_source` implies `location` | A source without coordinates is a producer bug |
| The document is not empty | An empty export is almost always a configuration mistake |

## Schema location

The schema is published twice: at `schemas/photo-record-v1.json` for
discoverability, and inside the package so that an installed copy is
self-contained. A test asserts the two are identical, so they cannot drift.
See ADR-0005.
