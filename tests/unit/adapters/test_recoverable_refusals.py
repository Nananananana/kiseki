"""A refusal the environment caused can be taken back."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import (
    SqliteSingleCaptionRepository,
    clear_recoverable,
    connect,
    count_recoverable,
)
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.photo.observation import PhotoId

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _single(name: str, refused: str | None) -> SingleCaption:
    return SingleCaption(
        photo_id=PhotoId(f"sha256:{name}"),
        text="" if refused else "a bowl of ramen",
        model="" if refused else "vl",
        created_at=WHEN,
        refused=refused,
    )


def _seeded(tmp_path: Path):
    connection = connect(tmp_path / "kiseki.sqlite3")
    repository = SqliteSingleCaptionRepository(connection)
    repository.save(_single("aa", "no thumbnail at 2026/08/aa.jpg"))
    repository.save(_single("bb", "no thumbnail at 2026/08/bb.jpg"))
    repository.save(_single("cc", "the model declined to describe this"))
    repository.save(_single("dd", None))
    return connection, repository


def test_only_the_environment_s_refusals_count(tmp_path: Path) -> None:
    connection, _repository = _seeded(tmp_path)
    assert count_recoverable(connection, "single_captions") == 2


def test_clearing_leaves_the_model_s_word_alone(tmp_path: Path) -> None:
    connection, repository = _seeded(tmp_path)
    assert clear_recoverable(connection, "single_captions") == 2
    assert count_recoverable(connection, "single_captions") == 0
    kept = repository.all()
    assert len(kept) == 2
    reasons = {caption.refused for caption in kept}
    assert "the model declined to describe this" in reasons


def test_a_table_without_refusals_is_refused(tmp_path: Path) -> None:
    connection = connect(tmp_path / "kiseki.sqlite3")
    with pytest.raises(ValueError):
        count_recoverable(connection, "theme_sets")
