"""Both photo repositories carry the thumbnail reference unchanged."""

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

from kiseki.adapters.memory.repositories import InMemoryPhotoRepository
from kiseki.adapters.sqlite.store import SqlitePhotoRepository, connect
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.ports.repositories import PhotoRepository

WHEN = datetime(2026, 5, 3, 10, tzinfo=timezone.utc)


def _observation(identifier: str, thumbnail_ref: str | None) -> PhotoObservation:
    return PhotoObservation(PhotoId(identifier), WHEN, thumbnail_ref=thumbnail_ref)


class ThumbnailContract:
    @pytest.fixture
    def photos(self) -> PhotoRepository:
        raise NotImplementedError("override the 'photos' fixture")

    def test_preserves_the_reference(self, photos: PhotoRepository) -> None:
        photos.save_all([_observation("sha256:aa", "2025/05/aa.jpg")])
        assert photos.all()[0].thumbnail_ref == "2025/05/aa.jpg"

    def test_preserves_its_absence(self, photos: PhotoRepository) -> None:
        photos.save_all([_observation("sha256:bb", None)])
        assert photos.all()[0].thumbnail_ref is None


class TestInMemoryThumbnails(ThumbnailContract):
    @pytest.fixture
    def photos(self) -> InMemoryPhotoRepository:
        return InMemoryPhotoRepository()


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = connect(tmp_path / "kiseki.sqlite3")
    yield handle
    handle.close()


class TestSqliteThumbnails(ThumbnailContract):
    @pytest.fixture
    def photos(self, connection: sqlite3.Connection) -> SqlitePhotoRepository:
        return SqlitePhotoRepository(connection)
