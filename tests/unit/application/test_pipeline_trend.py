"""The trend use case: compare the kept readings, through the themes.

Derivation itself is specified exactly in the trend derivation tests;
what is specified here is the seam. The pipeline reads the profile
history and the current theme set from storage, recomputes nothing,
and calls no model.
"""

from datetime import datetime, timedelta

from kiseki.adapters.fake.profiles import FakeProfileRepository
from kiseki.adapters.fake.themes import FakeThemeSetRepository
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline
from kiseki.domain.caption.themes import Theme, ThemeSet, ThemeSetKey
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.trends import TrendDirection

BASE = datetime(2026, 6, 1, 12)


def _interest(topic: str, score: float, confidence: float) -> Interest:
    evidence = (
        InterestEvidence(
            kind=EvidenceKind.PHOTOGRAPH,
            reference=f"caption:{topic}",
            observed_at=BASE,
        ),
    )
    return Interest(
        topic=topic,
        score=score,
        confidence=confidence,
        evidence=evidence,
        first_seen=BASE,
        last_seen=BASE,
    )


def _profile(days: int, *interests: Interest) -> Profile:
    return Profile(generated_at=BASE + timedelta(days=days), interests=interests)


def _pipeline(
    profiles: FakeProfileRepository | None = None,
    themes: FakeThemeSetRepository | None = None,
) -> Pipeline:
    return Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        profiles=profiles,
        themes=themes,
    )


class TestTrend:
    def test_without_a_profile_repository_there_is_no_trend(self) -> None:
        assert _pipeline().trend() is None

    def test_a_short_history_yields_no_trend(self) -> None:
        repository = FakeProfileRepository()
        repository.save(_profile(0, _interest("onsen", 0.5, 0.4)))
        assert _pipeline(profiles=repository).trend() is None

    def test_a_grown_history_yields_a_report(self) -> None:
        repository = FakeProfileRepository()
        repository.save(_profile(0, _interest("onsen", 0.5, 0.4)))
        repository.save(_profile(20, _interest("onsen", 0.9, 0.6)))
        report = _pipeline(profiles=repository).trend()
        assert report is not None
        assert report.trends[0].direction is TrendDirection.RISING

    def test_the_current_themes_shape_the_reading(self) -> None:
        repository = FakeProfileRepository()
        repository.save(_profile(0, _interest("tree", 0.6, 0.5)))
        repository.save(_profile(20, _interest("outdoor", 0.6, 0.5)))

        themes = FakeThemeSetRepository()
        themes.save(
            ThemeSet(
                key=ThemeSetKey.of(["tree", "mountain"]),
                themes=(Theme(name="outdoor", members=("tree", "mountain")),),
                model="fake",
                created_at=BASE,
            )
        )

        report = _pipeline(profiles=repository, themes=themes).trend()
        assert report is not None
        (trend,) = report.trends
        assert trend.topic == "outdoor"
        assert trend.direction is TrendDirection.STEADY

    def test_works_without_a_theme_repository(self) -> None:
        repository = FakeProfileRepository()
        repository.save(_profile(0, _interest("onsen", 0.5, 0.4)))
        repository.save(_profile(20, _interest("onsen", 0.5, 0.4)))
        assert _pipeline(profiles=repository).trend() is not None
