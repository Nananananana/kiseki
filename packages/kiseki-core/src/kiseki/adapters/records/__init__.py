"""Reading a PhotoRecord document, whole or a record at a time.

The whole-document reader is what this library has always had, and it
is right for the libraries most people have. Measured:

    records    on disk    peak memory    ratio    time
     50,000     29 MB        136 MB       4.7x     0.7 s
    200,000    116 MB        546 MB       4.7x     5.5 s

Linear, so a million records -- 580 MB of JSON, which a location
history reaches -- is about **2.7 GB** to read a document. Every
comparable project in this category streams; Dawarich's release notes
describe imports as handling millions of points.

So there is a second reader, behind an extra, on `ijson`. Measured
through the whole ingest path -- reading, converting, batching -- on
the same 200,000-record document, because the reader alone would be
a number about the reader alone:

    whole      545.8 MB peak  (4.69x the file)  12.2 s
    streaming   19.8 MB peak  (0.17x)           20.6 s

**Twenty-eight times less memory, at 1.7 times the time.** And the 19.8
MB is the batch, not the document, so it stays 19.8 MB at a million
records where the other reaches about 2.7 GB.

The trade is not close, and the reason is elsewhere in this library: a
first run on a library that size spends **hours** in the model (#381).
Eight seconds of ingest is invisible beside four hours of captioning.
546 MB on a laptop is not invisible at all.

## Why the slower one is the default anyway

Because the extra may not be installed, and a library of five thousand
photographs is 29 MB and 136 MB of peak -- fine, and faster. The
streaming reader is used when it is there, and this module says which
one ran rather than choosing silently.

## What streaming buys that is not memory

**A malformed record is reported as a record.** The whole-document
reader parses everything and then fails about the document: a 2 GB
file broken at record 900,000 costs four minutes and several gigabytes
to say *Expecting value: line 1 column 812...*. Streaming says which
record, having already handled the ones before it.
"""

from collections.abc import Iterator
from importlib.util import find_spec
from pathlib import Path
from typing import Any

EXTRA = "streaming"
REQUIRES = ("ijson",)

WHOLE = "whole"
STREAMING = "streaming"


def is_streaming_available() -> bool:
    return all(find_spec(name) is not None for name in REQUIRES)


def _refuse(message: str) -> None:
    raise ValueError(message)


def read_whole(path: Path) -> Iterator[dict[str, Any]]:
    """Parse the document, then hand back its records.

    Needs nothing, and costs about 4.7 times the file in memory.
    """
    import json

    document = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(document, dict) or "records" not in document:
        _refuse("not a PhotoRecord document: no 'records' key")
    records = document["records"]
    if not isinstance(records, list):
        _refuse("not a PhotoRecord document: 'records' is not a list")
    yield from records


def read_streaming(path: Path) -> Iterator[dict[str, Any]]:
    """Hand back each record as it is parsed.

    Constant memory, and a malformed record is reported as a record
    rather than as the document it was in.
    """
    import ijson

    index = 0
    with path.open("rb") as handle:
        try:
            # use_float, and it is not a preference. ijson decodes JSON
            # numbers to Decimal by default, `json` decodes them to
            # float, and sqlite3 refuses to bind a Decimal at all:
            # "Error binding parameter 3: type 'decimal.Decimal' is not
            # supported". Two readers of one document that disagree
            # about the type of a latitude are two readers, and the
            # cross-check test exists because this got through once.
            for record in ijson.items(handle, "records.item", use_float=True):
                if not isinstance(record, dict):
                    _refuse(f"record {index} is not an object")
                index += 1
                yield record
        except ijson.JSONError as error:
            _refuse(
                f"the document stops being readable at record {index}: {error}. "
                "The records before it were well formed, so this is where to look."
            )
    if index == 0 and not _has_records_key(path):
        _refuse("not a PhotoRecord document: no 'records' key")


def _has_records_key(path: Path) -> bool:
    """Whether the document has the key at all.

    A document with `"records": []` and a document with no `records`
    are both zero records to a streaming parser, and they are not the
    same thing: the first is an owner with no photographs and the
    second is the wrong file.
    """
    import ijson

    with path.open("rb") as handle:
        for prefix, event, _ in ijson.parse(handle):
            if prefix == "records" and event in {"start_array", "start_map"}:
                return True
    return False


def reader(path: Path, prefer_streaming: bool = True) -> tuple[Iterator[dict[str, Any]], str]:
    """The records, and the name of the reader that produced them."""
    if prefer_streaming and is_streaming_available():
        return read_streaming(path), STREAMING
    return read_whole(path), WHOLE
