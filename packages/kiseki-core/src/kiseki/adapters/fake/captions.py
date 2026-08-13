"""In-memory caption repository, for tests and examples."""

from __future__ import annotations

from kiseki.domain.caption.caption import Caption, CaptionKey


class FakeCaptionRepository:
    """Keeps captions in memory; conforms to CaptionRepository."""

    def __init__(self) -> None:
        self._by_key: dict[str, Caption] = {}
        self._order: list[str] = []

    def save(self, caption: Caption) -> None:
        if caption.key.value not in self._by_key:
            self._order.append(caption.key.value)
        self._by_key[caption.key.value] = caption

    def get(self, key: CaptionKey) -> Caption | None:
        return self._by_key.get(key.value)

    def all(self) -> tuple[Caption, ...]:
        return tuple(self._by_key[value] for value in self._order)
