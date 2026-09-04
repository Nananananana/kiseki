"""Conformance test kit for the contracts KISEKI reads and publishes.

Four contracts are checked here. [PhotoRecord v1] is the **input**: any
program, in any language, may emit it, and this kit lets that program
prove its output is acceptable without importing the library.
[kiseki-interest-export v1] is the **output**: the only document KISEKI
prepares for the world outside the machine, and the one other people
read. An input contract fails loudly at ingest when it is wrong; an
output contract fails quietly, in somebody else's program, which is
why it is checked here.

`NoteRecord v1` and `WebRecord v1` are the other two inputs, and they
are what a producer of readings emits: a category and some labels, and
never the text. **Neither document can name itself** -- both are bare
arrays of the same six field names, and the reference prefix is not an
identifier because the contract promises only that a reference is
stable and opaque. So the command line asks which you meant rather
than guessing, and the suites for these two assert that the kit does
*not* identify them.

`ActivityRecord v1` is deliberately absent: its converter waits for a
real export to exist, and a schema written now would be written
against an imagined document.

A producer does not need to be written in Python and does not need to
import the core library. The pytest suites are for producers that are;
``kiseki-conformance output.json`` is for the ones that are not.
"""

from kiseki_conformance.checks import (
    check_semantics,
    load_schema,
    validate_document,
)
from kiseki_conformance.contracts import (
    INTEREST_EXPORT,
    NOTE_RECORD,
    PHOTO_RECORD,
    WEB_RECORD,
    Contract,
    identify,
)
from kiseki_conformance.interest_export import (
    check_export_semantics,
    load_export_schema,
    validate_export,
)
from kiseki_conformance.readings import (
    check_note_semantics,
    check_web_semantics,
)
from kiseki_conformance.suite import (
    ContractConformance,
    InterestExportConformance,
    NoteRecordConformance,
    PhotoRecordConformance,
    WebRecordConformance,
)
from kiseki_conformance.trust import CASES, Case, TrustBoundaryConformance

__all__ = [
    "CASES",
    "INTEREST_EXPORT",
    "NOTE_RECORD",
    "PHOTO_RECORD",
    "WEB_RECORD",
    "Case",
    "Contract",
    "ContractConformance",
    "InterestExportConformance",
    "NoteRecordConformance",
    "PhotoRecordConformance",
    "TrustBoundaryConformance",
    "WebRecordConformance",
    "check_export_semantics",
    "check_note_semantics",
    "check_semantics",
    "check_web_semantics",
    "identify",
    "load_export_schema",
    "load_schema",
    "validate_document",
    "validate_export",
]
