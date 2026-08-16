"""Where corrections are kept. Append-only by contract."""

from __future__ import annotations

from typing import Protocol

from kiseki.domain.correction import Correction


class CorrectionRepository(Protocol):
    def add(self, correction: Correction) -> None: ...

    def all(self) -> tuple[Correction, ...]: ...
