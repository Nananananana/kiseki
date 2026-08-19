"""The trips command shows the nights away, and says when there are none."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqlitePhotoRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint
from kiseki.interfaces.cli import EXIT_OK, main

BASE = datetime(2026, 3, 1, 9, tzinfo=UTC)
HOME = GeoPoint(34.7810, 135.4690)
FAR = GeoPoint(37.5600, 126.9800)


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _seed(tmp_path: Path, away_days: int) -> None:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    photographs = []
    index = 0
    for week in range(8):
        when = BASE + timedelta(days=7 * week)
        for offset in range(3):
            index += 1
            photographs.append(
                PhotoObservation(
                    PhotoId(f"sha256:h{index:04d}"),
                    when + timedelta(minutes=15 * offset),
                    HOME,
                    content_kind="photo",
                )
            )
    for day in range(away_days):
        when = BASE + timedelta(days=100 + day)
        for offset in range(3):
            index += 1
            photographs.append(
                PhotoObservation(
                    PhotoId(f"sha256:a{index:04d}"),
                    when + timedelta(minutes=20 * offset),
                    FAR,
                    content_kind="photo",
                )
            )
    SqlitePhotoRepository(connection).save_all(photographs)
    connection.close()
    assert main(["--data-root", str(tmp_path), "build"]) == EXIT_OK


class TestTripsCommand:
    def test_an_empty_library_says_so(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "trips"]) == EXIT_OK
        assert "no trips yet" in capsys.readouterr().out

    def test_three_days_away_are_one_trip(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path, away_days=3)
        assert main(["--data-root", str(tmp_path), "trips"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "trips         1" in out
        assert "2 nights" in out

    def test_a_library_that_never_left_has_no_trips(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path, away_days=0)
        assert main(["--data-root", str(tmp_path), "trips"]) == EXIT_OK
        assert "no trips yet" in capsys.readouterr().out
