"""In-memory doubles for the screen reader and its repository."""

from collections.abc import Callable, Sequence

from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.screen.reading import SENSITIVE_CATEGORIES, ScreenshotReading
from kiseki.ports.models import Completion, ModelUnavailableError, Usage
from kiseki.ports.screens import ScreenRead


class FakeScreenshotReader:
    """Deterministic answers; a failure can be provoked."""

    def __init__(
        self,
        answer: Callable[[bytes], tuple[str, tuple[str, ...]]] | None = None,
        fail_on: Callable[[bytes], bool] | None = None,
        model: str = "fake-screen-reader",
    ) -> None:
        self._answer = answer if answer is not None else (lambda _: ("product", ("camera",)))
        self._fail_on = fail_on if fail_on is not None else (lambda _: False)
        self._model = model
        self._usage = Usage()
        self.seen: list[bytes] = []

    def read(self, images: Sequence[bytes]) -> list[ScreenRead]:
        results = []
        for image in images:
            self.seen.append(image)
            if self._fail_on(image):
                self._usage = self._usage.record_failure()
                raise ModelUnavailableError("the fake screen reader was told to fail")
            category, labels = self._answer(image)
            if category in SENSITIVE_CATEGORIES:
                labels = ()
            self._usage = self._usage.record(Completion(text=category, model=self._model))
            results.append(ScreenRead(category=category, labels=labels, model=self._model))
        return results

    @property
    def usage(self) -> Usage:
        return self._usage


class FakeScreenshotReadingRepository:
    """Keeps readings in memory; conforms to ScreenshotReadingRepository."""

    def __init__(self) -> None:
        self._by_id: dict[str, ScreenshotReading] = {}
        self._order: list[str] = []

    def save(self, reading: ScreenshotReading) -> None:
        if reading.photo_id.value not in self._by_id:
            self._order.append(reading.photo_id.value)
        self._by_id[reading.photo_id.value] = reading

    def get(self, photo_id: PhotoId) -> ScreenshotReading | None:
        return self._by_id.get(photo_id.value)

    def all(self) -> tuple[ScreenshotReading, ...]:
        return tuple(self._by_id[value] for value in self._order)
