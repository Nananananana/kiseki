"""The discover command shows what is worth a look, with its arithmetic."""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqliteProfileRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.interfaces.cli import EXIT_OK, main

BASE = datetime(2026, 6, 1, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _profile(days: int, topic: str) -> Profile:
    at = BASE + timedelta(days=days)
    evidence = (
        InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference="caption:aa", observed_at=at),
    )
    interest = Interest(
        topic=topic,
        score=0.6,
        confidence=0.5,
        evidence=evidence,
        first_seen=at,
        last_seen=at,
    )
    return Profile(generated_at=at, interests=(interest,))


def _seed(tmp_path: Path, *profiles: Profile) -> None:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    repository = SqliteProfileRepository(connection)
    for profile in profiles:
        repository.save(profile)
    connection.close()


class TestDiscoverCommand:
    def test_answers_an_empty_database(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "discover"]) == EXIT_OK
        assert "not enough history" in capsys.readouterr().out

    def test_shows_the_arithmetic(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _seed(tmp_path, _profile(0, "onsen"), _profile(20, "museum"))
        assert main(["--data-root", str(tmp_path), "discover"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "importance" in out
        assert "museum" in out
        assert main(["--data-root", str(tmp_path), "discover", "--json"]) == EXIT_OK
        payload = json.loads(capsys.readouterr().out)
        assert "importance" in payload["discoveries"][0]
