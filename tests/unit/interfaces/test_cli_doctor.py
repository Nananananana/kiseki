"""The doctor runs categorised, deterministic checks. It never fixes."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import (
    SqliteProfileRepository,
    SqliteSingleCaptionRepository,
    connect,
)
from kiseki.config.paths import resolve_paths
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.interests import Profile
from kiseki.domain.photo.observation import PhotoId
from kiseki.interfaces.cli import EXIT_OK, main

BASE = datetime(2026, 6, 1, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _run(tmp_path: Path) -> int:
    return main(["--data-root", str(tmp_path), "doctor"])


def _connection(tmp_path: Path):
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    return connect(paths.db_path)


class TestDoctorCommand:
    def test_every_category_speaks(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert _run(tmp_path) == EXIT_OK
        out = capsys.readouterr().out
        for category in ("[schema]", "[integrity]", "[privacy]", "[evidence]", "[consistency]"):
            assert category in out
        assert "no kept profile yet" in out

    def test_new_readings_hint_at_a_snapshot(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        connection = _connection(tmp_path)
        SqliteProfileRepository(connection).save(Profile(generated_at=BASE, interests=()))
        SqliteSingleCaptionRepository(connection).save(
            SingleCaption(PhotoId("sha256:aa"), "a bowl of ramen", "vl", BASE + timedelta(days=1))
        )
        connection.close()
        assert _run(tmp_path) == EXIT_OK
        out = capsys.readouterr().out
        assert "newer than the last kept profile" in out
        assert "kiseki profile" in out

    def test_a_fresh_snapshot_needs_no_hint(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        connection = _connection(tmp_path)
        SqliteSingleCaptionRepository(connection).save(
            SingleCaption(PhotoId("sha256:aa"), "a bowl of ramen", "vl", BASE)
        )
        SqliteProfileRepository(connection).save(
            Profile(generated_at=BASE + timedelta(days=1), interests=())
        )
        connection.close()
        assert _run(tmp_path) == EXIT_OK
        assert "nothing newer than the last kept profile" in capsys.readouterr().out

    def test_a_missing_gazetteer_is_said_plainly(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert _run(tmp_path) == EXIT_OK
        assert "places stay unnamed" in capsys.readouterr().out
