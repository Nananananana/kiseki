"""Both theme repositories honour the same contract."""

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from kiseki.adapters.fake.themes import FakeThemeSetRepository
from kiseki.adapters.sqlite.store import SqliteThemeSetRepository, connect
from kiseki.domain.caption.themes import Theme, ThemeSet, ThemeSetKey
from kiseki.ports.themes import ThemeSetRepository

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _theme_set(*labels: str) -> ThemeSet:
    universe = list(labels) or ["tree", "landscape"]
    return ThemeSet(
        key=ThemeSetKey.of(universe),
        themes=(Theme(name="outdoor", members=("tree", "landscape")),),
        model="fake-language-model",
        created_at=WHEN,
    )


class ThemeSetRepositoryContract:
    @pytest.fixture
    def themes(self) -> ThemeSetRepository:
        raise NotImplementedError("override the 'themes' fixture")

    def test_an_unknown_key_is_none(self, themes: ThemeSetRepository) -> None:
        assert themes.get(ThemeSetKey.of(["nothing"])) is None

    def test_latest_is_none_before_any_save(self, themes: ThemeSetRepository) -> None:
        assert themes.latest() is None

    def test_a_saved_set_is_recalled_whole(self, themes: ThemeSetRepository) -> None:
        saved = _theme_set()
        themes.save(saved)
        assert themes.get(saved.key) == saved

    def test_latest_returns_the_most_recent_save(self, themes: ThemeSetRepository) -> None:
        earlier = _theme_set("tree", "landscape")
        later = _theme_set("tree", "landscape", "car")
        themes.save(earlier)
        themes.save(later)
        assert themes.latest() == later

    def test_saving_the_same_key_replaces(self, themes: ThemeSetRepository) -> None:
        first = _theme_set()
        second = ThemeSet(
            key=first.key,
            themes=(Theme(name="nature", members=("tree", "landscape")),),
            model="fake-language-model",
            created_at=WHEN,
        )
        themes.save(first)
        themes.save(second)
        recalled = themes.get(first.key)
        assert recalled is not None
        assert recalled.themes[0].name == "nature"


class TestFakeThemeSetRepository(ThemeSetRepositoryContract):
    @pytest.fixture
    def themes(self) -> FakeThemeSetRepository:
        return FakeThemeSetRepository()


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = connect(tmp_path / "kiseki.sqlite3")
    yield handle
    handle.close()


class TestSqliteThemeSetRepository(ThemeSetRepositoryContract):
    @pytest.fixture
    def themes(self, connection: sqlite3.Connection) -> SqliteThemeSetRepository:
        return SqliteThemeSetRepository(connection)


class TestThemeSetPersistence:
    def test_a_theme_set_survives_reopening(self, tmp_path: Path) -> None:
        path = tmp_path / "kiseki.sqlite3"
        saved = _theme_set()

        first = connect(path)
        SqliteThemeSetRepository(first).save(saved)
        first.close()

        second = connect(path)
        try:
            assert SqliteThemeSetRepository(second).get(saved.key) == saved
        finally:
            second.close()
