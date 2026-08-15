"""Non-photograph records never shape stops or anchors.

They are stored and counted, and later versions read them as interest
evidence, but the journey reconstruction sees camera photographs
only. See ADR-0028.
"""

from datetime import datetime, timedelta, timezone

from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint

BASE = datetime(2026, 6, 1, 10, tzinfo=timezone(timedelta(hours=9)))


def _observation(index: int, kind: str) -> PhotoObservation:
    return PhotoObservation(
        PhotoId(f"p{index}"),
        BASE + timedelta(minutes=20 * index),
        GeoPoint(35.0, 135.0),
        thumbnail_ref=None,
        content_kind=kind,
    )


def _pipeline() -> Pipeline:
    return Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
    )


class TestJourneysExcludeNonPhotos:
    def test_this_shape_of_photographs_forms_a_stop(self) -> None:
        """The baseline: the exclusion test below rests on this data
        being enough for a stop when it is made of photographs."""
        pipeline = _pipeline()
        pipeline.ingest([_observation(index, "photo") for index in range(6)])
        assert pipeline.rebuild().stops >= 1

    def test_the_same_shape_of_screenshots_forms_none(self) -> None:
        pipeline = _pipeline()
        pipeline.ingest([_observation(index, "screenshot") for index in range(6)])
        result = pipeline.rebuild()
        assert result.stops == 0
        assert result.photographs == 6
