"""The suggest command offers only what the owner's evidence holds."""

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


def _profile(days: int, *topics: str) -> Profile:
    at = BASE + timedelta(days=days)
    interests = tuple(
        Interest(
            topic=topic,
            score=0.6,
            confidence=0.5,
            evidence=(
                InterestEvidence(
                    kind=EvidenceKind.PHOTOGRAPH, reference="caption:aa", observed_at=at
                ),
            ),
            first_seen=at,
            last_seen=at,
        )
        for topic in topics
    )
    return Profile(generated_at=at, interests=interests)


class TestSuggestCommand:
    def test_answers_an_empty_database(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "suggest"]) == EXIT_OK
        assert "nothing to suggest" in capsys.readouterr().out

    def test_offers_a_dormant_interest_back(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        connection = connect(paths.db_path)
        repository = SqliteProfileRepository(connection)
        repository.save(_profile(0, "skiing", "museum"))
        repository.save(_profile(20, "skiing", "museum"))
        repository.save(_profile(40, "museum"))
        connection.close()
        assert main(["--data-root", str(tmp_path), "suggest"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "pick up" in out
        assert "skiing" in out

    def test_without_outings_the_reach_is_not_claimed(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """No outings, no reach: the command says nothing it cannot support."""
        assert main(["--data-root", str(tmp_path), "suggest"]) == EXIT_OK
        assert "your outings cover under" not in capsys.readouterr().out
