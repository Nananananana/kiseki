"""A command that reads is safe to run twice.

The profile kept a snapshot every time it printed one, so reading the
history meant reading how often somebody had typed a command. Nothing
failed when it did. This does. See ADR-0070.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import (
    SqlitePhotoRepository,
    SqliteProfileRepository,
    connect,
)
from kiseki.config.paths import resolve_paths
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint
from kiseki.interfaces.cli import EXIT_OK, main

BASE = datetime(2026, 6, 1, 9, tzinfo=UTC)
HOME = GeoPoint(34.7810, 135.4690)


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
        [
            PhotoObservation(
                PhotoId(f"sha256:p{index:04d}"),
                BASE + timedelta(minutes=15 * index),
                HOME,
            )
            for index in range(6)
        ]
    )
    connection.close()
    assert main(["--data-root", str(tmp_path), "build"]) == EXIT_OK


def _kept(tmp_path: Path) -> int:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    return len(SqliteProfileRepository(connect(paths.db_path)).history())


def test_printing_the_profile_keeps_nothing(tmp_path: Path) -> None:
    _seed(tmp_path)
    before = _kept(tmp_path)
    for _run in range(3):
        assert main(["--data-root", str(tmp_path), "profile"]) == EXIT_OK
    assert _kept(tmp_path) == before


def test_keep_keeps(tmp_path: Path) -> None:
    _seed(tmp_path)
    before = _kept(tmp_path)
    assert main(["--data-root", str(tmp_path), "profile", "--keep"]) == EXIT_OK
    assert _kept(tmp_path) == before + 1


def test_json_reading_keeps_nothing_either(tmp_path: Path) -> None:
    _seed(tmp_path)
    before = _kept(tmp_path)
    assert main(["--data-root", str(tmp_path), "profile", "--json"]) == EXIT_OK
    assert _kept(tmp_path) == before
