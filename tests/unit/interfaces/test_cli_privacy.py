"""The privacy command reports, and promises only what code enforces."""

import json
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env beside the repo."""
    monkeypatch.chdir(tmp_path)


class TestPrivacyCommand:
    def test_reports_an_empty_database(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "privacy"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "photographs" in out
        assert "never stored" in out
        assert "screenshot text" in out

    def test_json_carries_the_counts(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "privacy", "--json"]) == EXIT_OK
        payload = json.loads(capsys.readouterr().out)
        assert payload["photographs"] == 0
        assert "never_stored" in payload


def test_screen_readings_are_counted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from datetime import UTC, datetime

    from kiseki.adapters.sqlite.store import SqliteScreenshotReadingRepository, connect
    from kiseki.config.paths import resolve_paths
    from kiseki.domain.photo.observation import PhotoId
    from kiseki.domain.screen.reading import ScreenshotReading

    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    repository = SqliteScreenshotReadingRepository(connection)
    repository.save(
        ScreenshotReading(
            PhotoId("sha256:s1"), "map", ("route",), "vl", datetime(2026, 6, 1, tzinfo=UTC), None
        )
    )
    repository.save(
        ScreenshotReading(
            PhotoId("sha256:s2"), "chat", (), "vl", datetime(2026, 6, 1, tzinfo=UTC), None
        )
    )
    connection.close()
    assert main(["--data-root", str(tmp_path), "privacy", "--json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["screen_readings"] == 2
    assert payload["screens_label_silent"] == 1
