"""In-memory single-caption repository, for tests and examples."""

from __future__ import annotations

from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.photo.observation import PhotoId


class FakeSingleCaptionRepository:
    """Keeps captions in memory; conforms to SingleCaptionRepository."""

    def __init__(self) -> None:
        self._by_id: dict[str, SingleCaption] = {}
        self._order: list[str] = []

    def save(self, caption: SingleCaption) -> None:
        if caption.photo_id.value not in self._by_id:
            self._order.append(caption.photo_id.value)
        self._by_id[caption.photo_id.value] = caption

    def get(self, photo_id: PhotoId) -> SingleCaption | None:
        return self._by_id.get(photo_id.value)

    def all(self) -> tuple[SingleCaption, ...]:
        return tuple(self._by_id[value] for value in self._order)
