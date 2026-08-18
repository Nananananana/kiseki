"""Which readings a new prompt version left behind, and clearing them."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import (
    SqliteCaptionRepository,
    SqliteThemeSetRepository,
    clear_outdated,
    connect,
    count_outdated,
)
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.themes import Theme, ThemeSet, ThemeSetKey
from kiseki.domain.photo.observation import PhotoId

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _caption(name: str, version: str | None, refused: str | None = None) -> Caption:
    key = CaptionKey.of([PhotoId(f"sha256:{name}")])
    return Caption(
        key=key,
        photo_ids=(PhotoId(f"sha256:{name}"),),
        text="" if refused else "a bowl of ramen",
        model="" if refused else "vl",
        created_at=WHEN,
        refused=refused,
        prompt_version=version,
    )


def _seeded(tmp_path: Path):
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteCaptionRepository(connection)
    repository.save(_caption("aa", "stay-caption/1"))
    repository.save(_caption("bb", "stay-caption/0"))
    repository.save(_caption("cc", None))
    repository.save(_caption("dd", None, refused="no thumbnail"))
    return connection, repository


def test_older_and_unrecorded_readings_are_counted(tmp_path: Path) -> None:
    connection, _repository = _seeded(tmp_path)
    assert count_outdated(connection, "captions", "stay-caption/1") == 2


def test_a_refusal_is_left_out_of_the_count(tmp_path: Path) -> None:
    connection, repository = _seeded(tmp_path)
    clear_outdated(connection, "captions", "stay-caption/1")
    kept = {caption.key.value for caption in repository.all()}
    refused = _caption("dd", None, refused="no thumbnail")
    assert refused.key.value in kept


def test_clearing_removes_exactly_the_outdated(tmp_path: Path) -> None:
    connection, repository = _seeded(tmp_path)
    assert clear_outdated(connection, "captions", "stay-caption/1") == 2
    assert count_outdated(connection, "captions", "stay-caption/1") == 0
    assert len(repository.all()) == 2


def test_a_table_without_refusals_still_works(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    key = ThemeSetKey.of(["ramen", "udon"])
    SqliteThemeSetRepository(connection).save(
        ThemeSet(
            key=key,
            themes=(Theme(name="food", members=("ramen", "udon")),),
            model="lm",
            created_at=WHEN,
            prompt_version="themes/0",
        )
    )
    assert count_outdated(connection, "theme_sets", "themes/1") == 1
    assert clear_outdated(connection, "theme_sets", "themes/1") == 1


def test_an_unknown_table_is_refused(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    with pytest.raises(ValueError):
        count_outdated(connection, "photos", "anything")
