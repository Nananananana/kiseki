"""Forgetting is shown before it is done."""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import (
    SqliteCaptionRepository,
    SqlitePhotoRepository,
    SqliteSingleCaptionRepository,
    connect,
)
from kiseki.config.paths import resolve_paths
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)
DOOMED = PhotoId("sha256:doomed")
SPARED = PhotoId("sha256:spared")


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _seed(tmp_path: Path) -> None:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    SqlitePhotoRepository(connection).save_all(
        [PhotoObservation(DOOMED, WHEN), PhotoObservation(SPARED, WHEN)]
    )
    SqliteCaptionRepository(connection).save(
        Caption(
            key=CaptionKey.of([DOOMED]),
            photo_ids=(DOOMED,),
            text="a bowl of ramen",
            model="vl",
            created_at=WHEN,
        )
    )
    SqliteSingleCaptionRepository(connection).save(
        SingleCaption(photo_id=DOOMED, text="a doorway", model="vl", created_at=WHEN)
    )
    connection.close()


class TestForgetCommand:
    def test_it_shows_before_it_does(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), "forget", DOOMED.value]) == EXIT_OK
        out = capsys.readouterr().out
        assert "would forget" in out
        assert "--apply" in out
        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        connection = connect(paths.db_path)
        assert len(SqlitePhotoRepository(connection).all()) == 2

    def test_apply_removes_exactly_that(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), "forget", DOOMED.value, "--apply"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "forgotten" in out
        assert "kiseki build" in out
        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        connection = connect(paths.db_path)
        remaining = SqlitePhotoRepository(connection).all()
        assert [photo.photo_id for photo in remaining] == [SPARED]
        assert SqliteSingleCaptionRepository(connection).get(DOOMED) is None

    def test_a_photograph_nobody_has_is_said_plainly(self, tmp_path: Path) -> None:
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), "forget", "sha256:nothing"]) == EXIT_BAD_INPUT
