"""Both caption repositories honour the same contract."""

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from kiseki.adapters.fake.captions import FakeCaptionRepository
from kiseki.adapters.sqlite.store import SqliteCaptionRepository, connect
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.photo.observation import PhotoId
from kiseki.ports.captions import CaptionRepository

WHEN = datetime(2026, 5, 3, 10, tzinfo=UTC)


def _caption(identifier: str = "sha256:aa", refused: str | None = None) -> Caption:
    photo_ids = (PhotoId(identifier),)
    return Caption(
        key=CaptionKey.of(photo_ids),
        photo_ids=photo_ids,
        text="" if refused else "a scene",
        model="" if refused else "fake-captioner",
        created_at=WHEN,
        refused=refused,
    )


class CaptionRepositoryContract:
    @pytest.fixture
    def captions(self) -> CaptionRepository:
        raise NotImplementedError("override the 'captions' fixture")

    def test_an_unknown_key_is_none(self, captions: CaptionRepository) -> None:
        assert captions.get(CaptionKey.of([PhotoId("sha256:zz")])) is None

    def test_a_saved_caption_is_recalled_whole(self, captions: CaptionRepository) -> None:
        caption = _caption()
        captions.save(caption)
        assert captions.get(caption.key) == caption

    def test_a_refusal_round_trips(self, captions: CaptionRepository) -> None:
        refusal = _caption(refused="image too large")
        captions.save(refusal)
        recalled = captions.get(refusal.key)
        assert recalled is not None
        assert recalled.refused == "image too large"
        assert not recalled.answered

    def test_saving_the_same_key_replaces(self, captions: CaptionRepository) -> None:
        photo_ids = (PhotoId("sha256:aa"),)
        key = CaptionKey.of(photo_ids)
        first = Caption(key, photo_ids, "first reading", "m", WHEN)
        second = Caption(key, photo_ids, "second reading", "m", WHEN)
        captions.save(first)
        captions.save(second)
        recalled = captions.get(key)
        assert recalled is not None
        assert recalled.text == "second reading"

    def test_all_keeps_the_order_of_saving(self, captions: CaptionRepository) -> None:
        first = _caption("sha256:aa")
        second = _caption("sha256:bb")
        captions.save(first)
        captions.save(second)
        assert captions.all() == (first, second)


class TestFakeCaptionRepository(CaptionRepositoryContract):
    @pytest.fixture
    def captions(self) -> FakeCaptionRepository:
        return FakeCaptionRepository()


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = connect(tmp_path / "kiseki.sqlite3")
    yield handle
    handle.close()


class TestSqliteCaptionRepository(CaptionRepositoryContract):
    @pytest.fixture
    def captions(self, connection: sqlite3.Connection) -> SqliteCaptionRepository:
        return SqliteCaptionRepository(connection)


class TestCaptionPersistence:
    def test_a_caption_survives_reopening(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        saved = _caption()

        first = connect(path)
        SqliteCaptionRepository(first).save(saved)
        first.close()

        second = connect(path)
        try:
            assert SqliteCaptionRepository(second).get(saved.key) == saved
        finally:
            second.close()
