"""Every implementation of the trust boundary, against one table.

There are two today and a third is coming, and they are separate on
purpose (ADR-0073): a producer that imported the core's version could
not be rewritten in another language, and the record contract would be
the only thing the two sides share in name only. The duplication is the
design. The unchecked duplication was the defect, and
`kiseki_notes/trust.py` said so in its own first paragraph while the
table it asked for did not exist.
"""

from collections.abc import Sequence

import pytest
from kiseki.domain.trust import TrustBoundary, judge
from kiseki_conformance import TrustBoundaryConformance
from kiseki_notes import trust as notes_trust


class TestTheCoreDecides(TrustBoundaryConformance):
    """`kiseki.domain.trust`, which guards a reduced photograph."""

    @pytest.fixture
    def admits(self):  # type: ignore[no-untyped-def]
        def decide(endpoint: str, boundary: str, trusted: Sequence[str]) -> bool:
            return judge(endpoint, TrustBoundary(boundary), trusted).admitted

        return decide


class TestTheNotesProducerDecides(TrustBoundaryConformance):
    """`kiseki_notes.trust`, which guards the text of a note."""

    @pytest.fixture
    def admits(self):  # type: ignore[no-untyped-def]
        def decide(endpoint: str, boundary: str, trusted: Sequence[str]) -> bool:
            return notes_trust.admitted(notes_trust.host_of(endpoint), boundary, tuple(trusted))

        return decide
