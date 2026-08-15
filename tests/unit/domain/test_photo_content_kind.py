"""The content kind travels with the observation.

PhotoRecord v1 has always said what a record is -- photo, screenshot,
document, other -- and the domain used to drop it. Now it is carried,
and it decides one thing: whether the observation may shape stops and
anchors. A screenshot has a location, but not one that was chosen.
See ADR-0028.
"""

from datetime import UTC, datetime

from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint

AT = datetime(2026, 6, 1, 10, tzinfo=UTC)


def _observation(kind: str | None) -> PhotoObservation:
    return PhotoObservation(
        PhotoId("p1"),
        AT,
        GeoPoint(35.0, 135.0),
        thumbnail_ref=None,
        content_kind=kind,
    )


class TestContentKind:
    def test_defaults_to_none(self) -> None:
        observation = PhotoObservation(PhotoId("p1"), AT)
        assert observation.content_kind is None

    def test_photographs_and_legacy_records_join_journeys(self) -> None:
        assert _observation("photo").joins_journeys
        assert _observation(None).joins_journeys

    def test_other_kinds_never_shape_stops_or_anchors(self) -> None:
        assert not _observation("screenshot").joins_journeys
        assert not _observation("document").joins_journeys
        assert not _observation("other").joins_journeys
