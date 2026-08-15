"""A reading can be taken without keeping it.

The HTTP interface answers GETs, and a GET must change nothing: a
served profile is a look at the current reading, not a new entry in
the history a trend is computed from. See ADR-0026.
"""

from datetime import datetime

from kiseki.adapters.fake.profiles import FakeProfileRepository
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline

GENERATED = datetime(2026, 6, 1, 12)


def _pipeline(profiles: FakeProfileRepository) -> Pipeline:
    return Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        profiles=profiles,
    )


class TestProfileWithoutKeeping:
    def test_the_reading_is_not_saved(self) -> None:
        repository = FakeProfileRepository()
        _pipeline(repository).profile(generated_at=GENERATED, keep=False)
        assert repository.history() == ()

    def test_the_reading_itself_is_still_given(self) -> None:
        repository = FakeProfileRepository()
        profile = _pipeline(repository).profile(generated_at=GENERATED, keep=False)
        assert profile.generated_at == GENERATED