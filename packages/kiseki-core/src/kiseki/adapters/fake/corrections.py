"""In-memory corrections, for tests and for wiring without a database."""

from __future__ import annotations

from kiseki.domain.correction import Correction


class FakeCorrectionRepository:
    def __init__(self) -> None:
        self._records: list[Correction] = []

    def add(self, correction: Correction) -> None:
        self._records.append(correction)

    def all(self) -> tuple[Correction, ...]:
        return tuple(self._records)
