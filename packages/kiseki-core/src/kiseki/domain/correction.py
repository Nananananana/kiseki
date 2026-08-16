"""The owner's word against a reading, kept forever, applied at read.

A correction never edits raw evidence and never rewrites a kept
profile: it is appended to a log, and every derivation reads through
the log, the way consent is honoured (ADR-0032). The latest word per
reference wins, so an exclusion can be reinstated by appending, not
by deleting. See ADR-0044.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique


@unique
class CorrectionVerdict(Enum):
    EXCLUDED = "excluded"
    REINSTATED = "reinstated"


@dataclass(frozen=True)
class Correction:
    """One appended word about one reference."""

    reference: str
    verdict: CorrectionVerdict
    note: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.reference.strip():
            raise ValueError("a correction needs a reference")


def active_exclusions(records: Sequence[Correction]) -> frozenset[str]:
    """The references currently excluded: the latest word per reference."""
    latest: dict[str, Correction] = {}
    for record in sorted(records, key=lambda record: record.created_at):
        latest[record.reference] = record
    return frozenset(
        reference
        for reference, record in latest.items()
        if record.verdict is CorrectionVerdict.EXCLUDED
    )
