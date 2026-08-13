"""In-memory subject repository, for tests and examples."""

from __future__ import annotations

from kiseki.domain.caption.caption import CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction


class FakeSubjectRepository:
    """Keeps readings in memory; conforms to SubjectRepository."""

    def __init__(self) -> None:
        self._by_key: dict[str, SubjectExtraction] = {}
        self._order: list[str] = []

    def save(self, reading: SubjectExtraction) -> None:
        if reading.key.value not in self._by_key:
            self._order.append(reading.key.value)
        self._by_key[reading.key.value] = reading

    def get(self, key: CaptionKey) -> SubjectExtraction | None:
        return self._by_key.get(key.value)

    def all(self) -> tuple[SubjectExtraction, ...]:
        return tuple(self._by_key[value] for value in self._order)
