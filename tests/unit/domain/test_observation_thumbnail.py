"""The thumbnail reference rides along, opaque to the domain.

PhotoRecord v1 requires thumbnail_ref; the domain carries it as an
opaque string so an adapter can later resolve it to pixels. The domain
itself still never touches a file. See ADR-0018.
"""

from datetime import UTC, datetime

from kiseki.domain.photo.observation import PhotoId, PhotoObservation

WHEN = datetime(2026, 5, 3, 10, tzinfo=UTC)


class TestThumbnailReference:
    def test_defaults_to_none(self) -> None:
        observation = PhotoObservation(PhotoId("sha256:aa"), WHEN)
        assert observation.thumbnail_ref is None

    def test_carries_the_reference_when_given(self) -> None:
        observation = PhotoObservation(PhotoId("sha256:aa"), WHEN, thumbnail_ref="2025/05/aa.jpg")
        assert observation.thumbnail_ref == "2025/05/aa.jpg"
