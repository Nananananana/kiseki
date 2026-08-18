"""The drift command lays the timelines side by side and blames nobody."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqlitePhotoRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint
from kiseki.interfaces.cli import EXIT_OK, main

BASE = datetime(2026, 1, 15, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _seed(tmp_path: Path, months: int) -> None:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    photographs = []
    index = 0
    for month in range(months):
        when = BASE + timedelta(days=30 * month)
        for offset in range(3):
            index += 1
            photographs.append(
                PhotoObservation(
                    PhotoId(f"sha256:d{index:04d}"),
                    when + timedelta(minutes=10 * offset),
                    GeoPoint(34.78, 135.47),
                    content_kind="photo",
                )
            )
    SqlitePhotoRepository(connection).save_all(photographs)
    connection.close()
    assert main(["--data-root", str(tmp_path), "build"]) == EXIT_OK


class TestDriftCommand:
    def test_an_empty_library_says_so(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "drift"]) == EXIT_OK
        assert "not enough history" in capsys.readouterr().out

    def test_the_timelines_are_named_and_the_caution_is_printed(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path, months=6)
        assert main(["--data-root", str(tmp_path), "drift"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "photographs" in out
        assert "outings" in out
        assert "not causing" in out

    def test_each_series_stands_against_its_own_past(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path, months=6)
        assert main(["--data-root", str(tmp_path), "drift"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "against its own history" in out or "drifting" in out
