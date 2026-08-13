"""The profile use case: read the measures as interests, keep the reading.

Derivation itself is specified exactly in the interest derivation
tests; what is specified here is the seam. The pipeline reads storage
without recomputing, saves the reading when it has somewhere to save
it, and works without.
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


def _pipeline(profiles: FakeProfileRepository | None = None) -> Pipeline:
    return Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        profiles=profiles,
    )


class TestProfile:
    def test_an_empty_library_yields_an_empty_profile(self) -> None:
        profile = _pipeline().profile(generated_at=GENERATED)
        assert profile.interests == ()
        assert profile.generated_at == GENERATED

    def test_generated_at_defaults_to_now(self) -> None:
        before = datetime.now()
        profile = _pipeline().profile()
        after = datetime.now()
        assert before <= profile.generated_at <= after

    def test_the_reading_is_saved_when_a_repository_was_given(self) -> None:
        repository = FakeProfileRepository()
        profile = _pipeline(repository).profile(generated_at=GENERATED)
        assert repository.latest() == profile

    def test_every_reading_joins_the_history(self) -> None:
        repository = FakeProfileRepository()
        pipeline = _pipeline(repository)
        pipeline.profile(generated_at=datetime(2026, 6, 1))
        pipeline.profile(generated_at=datetime(2026, 6, 2))
        assert len(repository.history()) == 2

    def test_works_without_a_repository(self) -> None:
        profile = _pipeline().profile(generated_at=GENERATED)
        assert profile.interests == ()
