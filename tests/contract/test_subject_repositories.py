"""Both subject repositories honour the same contract."""

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

from kiseki.adapters.fake.subjects import FakeSubjectRepository
from kiseki.adapters.sqlite.store import SqliteSubjectRepository, connect
from kiseki.domain.caption.caption import CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.photo.observation import PhotoId
from kiseki.ports.subjects import SubjectRepository

WHEN = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)


def _reading(identifier: str = "sha256:aa", refused: str | None = None) -> SubjectExtraction:
    return SubjectExtraction(
        key=CaptionKey.of([PhotoId(identifier)]),
        labels=() if refused else ("ramen", "wooden counter"),
        model="" if refused else "fake-language-model",
        created_at=WHEN,
        refused=refused,
    )


class SubjectRepositoryContract:
    @pytest.fixture
    def subjects(self) -> SubjectRepository:
        raise NotImplementedError("override the 'subjects' fixture")

    def test_an_unknown_key_is_none(self, subjects: SubjectRepository) -> None:
        assert subjects.get(CaptionKey.of([PhotoId("sha256:zz")])) is None

    def test_a_saved_reading_is_recalled_whole(self, subjects: SubjectRepository) -> None:
        reading = _reading()
        subjects.save(reading)
        assert subjects.get(reading.key) == reading

    def test_a_refusal_round_trips(self, subjects: SubjectRepository) -> None:
        refusal = _reading(refused="unparseable answer")
        subjects.save(refusal)
        recalled = subjects.get(refusal.key)
        assert recalled is not None
        assert not recalled.answered

    def test_saving_the_same_key_replaces(self, subjects: SubjectRepository) -> None:
        key = CaptionKey.of([PhotoId("sha256:aa")])
        first = SubjectExtraction(key, ("first",), "m", WHEN)
        second = SubjectExtraction(key, ("second",), "m", WHEN)
        subjects.save(first)
        subjects.save(second)
        recalled = subjects.get(key)
        assert recalled is not None
        assert recalled.labels == ("second",)

    def test_all_keeps_the_order_of_saving(self, subjects: SubjectRepository) -> None:
        first = _reading("sha256:aa")
        second = _reading("sha256:bb")
        subjects.save(first)
        subjects.save(second)
        assert subjects.all() == (first, second)


class TestFakeSubjectRepository(SubjectRepositoryContract):
    @pytest.fixture
    def subjects(self) -> FakeSubjectRepository:
        return FakeSubjectRepository()


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = connect(tmp_path / "kiseki.sqlite3")
    yield handle
    handle.close()


class TestSqliteSubjectRepository(SubjectRepositoryContract):
    @pytest.fixture
    def subjects(self, connection: sqlite3.Connection) -> SqliteSubjectRepository:
        return SqliteSubjectRepository(connection)


class TestSubjectPersistence:
    def test_a_reading_survives_reopening(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        saved = _reading()

        first = connect(path)
        SqliteSubjectRepository(first).save(saved)
        first.close()

        second = connect(path)
        try:
            assert SqliteSubjectRepository(second).get(saved.key) == saved
        finally:
            second.close()
