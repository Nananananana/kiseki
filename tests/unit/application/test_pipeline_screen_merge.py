"""The profile picks up the screen readings when a store is wired."""

from datetime import datetime, timedelta

from kiseki.adapters.fake.screens import FakeScreenshotReadingRepository
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline
from kiseki.domain.interests import EvidenceKind
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.screen.reading import ScreenshotReading

AT = datetime(2026, 6, 1, 12)


def _pipeline(screens: FakeScreenshotReadingRepository | None = None) -> Pipeline:
    return Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        screens=screens,
    )


def _seeded() -> FakeScreenshotReadingRepository:
    screens = FakeScreenshotReadingRepository()
    for index in range(3):
        screens.save(
            ScreenshotReading(
                photo_id=PhotoId(f"s{index}"),
                category="product",
                labels=("camera",),
                model="m",
                created_at=AT + timedelta(days=index),
            )
        )
    return screens


class TestProfileMergesScreens:
    def test_without_a_store_nothing_changes(self) -> None:
        profile = _pipeline().profile(generated_at=AT, keep=False)
        assert profile.interests == ()

    def test_screen_interests_join_the_profile(self) -> None:
        profile = _pipeline(screens=_seeded()).profile(generated_at=AT, keep=False)
        (interest,) = profile.interests
        assert interest.topic == "camera"
        assert interest.evidence[0].kind is EvidenceKind.SCREENSHOT
