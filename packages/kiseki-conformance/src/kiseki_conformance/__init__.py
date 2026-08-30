"""Conformance test kit for the contracts KISEKI reads and publishes.

Two contracts are checked here. [PhotoRecord v1] is the **input**: any
program, in any language, may emit it, and this kit lets that program
prove its output is acceptable without importing the library.
[kiseki-interest-export v1] is the **output**: the only document KISEKI
prepares for the world outside the machine, and the one other people
read. An input contract fails loudly at ingest when it is wrong; an
output contract fails quietly, in somebody else's program, which is
why it is checked here.

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
    PHOTO_RECORD,
    Contract,
    identify,
)
from kiseki_conformance.interest_export import (
    check_export_semantics,
    load_export_schema,
    validate_export,
)
from kiseki_conformance.suite import (
    ContractConformance,
    InterestExportConformance,
    PhotoRecordConformance,
)
from kiseki_conformance.trust import CASES, Case, TrustBoundaryConformance

__all__ = [
    "CASES",
    "INTEREST_EXPORT",
    "PHOTO_RECORD",
    "Case",
    "Contract",
    "ContractConformance",
    "InterestExportConformance",
    "PhotoRecordConformance",
    "TrustBoundaryConformance",
    "check_export_semantics",
    "check_semantics",
    "identify",
    "load_export_schema",
    "load_schema",
    "validate_document",
    "validate_export",
]
