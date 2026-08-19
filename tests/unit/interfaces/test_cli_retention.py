"""Retention says what it would let go, and lets go of nothing unasked."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqlitePhotoRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.interfaces.cli import EXIT_OK, main

NOW = datetime.now(UTC)


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
            PhotoObservation(PhotoId("sha256:ancient"), NOW - timedelta(days=1200)),
            PhotoObservation(PhotoId("sha256:recent"), NOW - timedelta(days=5)),
        ]
    )
    connection.close()


class TestRetentionCommand:
    def test_no_rules_means_nothing_is_forgotten(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), "retention"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "nothing is forgotten" in out
        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        assert len(SqlitePhotoRepository(connect(paths.db_path)).all()) == 2

    def test_a_rule_counts_without_applying(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert (
            main(
                [
                    "--data-root",
                    str(tmp_path),
                    "retention",
                    "--keep-photographs-years",
                    "2",
                ]
            )
            == EXIT_OK
        )
        out = capsys.readouterr().out
        assert "would forget" in out
        assert "--apply" in out
        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        assert len(SqlitePhotoRepository(connect(paths.db_path)).all()) == 2

    def test_applying_lets_the_old_ones_go(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert (
            main(
                [
                    "--data-root",
                    str(tmp_path),
                    "retention",
                    "--keep-photographs-years",
                    "2",
                    "--apply",
                ]
            )
            == EXIT_OK
        )
        assert "forgotten" in capsys.readouterr().out
        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        remaining = SqlitePhotoRepository(connect(paths.db_path)).all()
        assert [photo.photo_id.value for photo in remaining] == ["sha256:recent"]
