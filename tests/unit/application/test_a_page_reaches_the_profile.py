"""Pages were stored and derived from nothing (#350). Now they reach the
profile, last, with their own evidence kind (ADR-0089)."""

from collections.abc import Sequence
from datetime import UTC, date, datetime

from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline, PipelineSettings
from kiseki.domain.interests import EvidenceKind
from kiseki.domain.shared.settings import PageSettings
from kiseki.domain.web.reading import PageReading

WHEN = datetime(2026, 9, 1, tzinfo=UTC)


class _Pages:
    def __init__(self, readings: Sequence[PageReading]) -> None:
        self._readings = tuple(readings)

    def all(self) -> tuple[PageReading, ...]:
        return self._readings


def _opened(label: str, days: int) -> list[PageReading]:
    return [
        PageReading(
            reference="page:a",
            day=date(2026, 3, 1 + index),
            category="reading",
            labels=(label,),
            model="demo",
            created_at=WHEN,
        )
        for index in range(days)
    ]


def _pipeline(
    readings: Sequence[PageReading], settings: PipelineSettings | None = None
) -> Pipeline:
    return Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        settings=settings,
        pages=_Pages(readings),  # type: ignore[arg-type]
    )


def test_a_page_opened_on_four_days_is_in_the_profile() -> None:
    profile = _pipeline(_opened("raft", 4)).profile(keep=False)
    raft = next(interest for interest in profile.interests if interest.topic == "raft")
    assert raft.evidence[0].kind is EvidenceKind.PAGE


def test_three_days_is_not_yet() -> None:
    profile = _pipeline(_opened("raft", 3)).profile(keep=False)
    assert "raft" not in {interest.topic for interest in profile.interests}


def test_the_owner_s_threshold_reaches_the_derivation() -> None:
    """A setting nothing reads is a constant with extra steps."""
    settings = PipelineSettings(pages=PageSettings(min_days=2, confidence_full_days=4))
    profile = _pipeline(_opened("raft", 2), settings).profile(keep=False)
    assert "raft" in {interest.topic for interest in profile.interests}
