"""The insights command holds coexisting tendencies side by side."""

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


def _interest(topic: str, score: float, confidence: float, at: datetime) -> Interest:
    evidence = (
        InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference="caption:aa", observed_at=at),
    )
    return Interest(
        topic=topic,
        score=score,
        confidence=confidence,
        evidence=evidence,
        first_seen=at,
        last_seen=at,
    )


def test_held_together_is_said_and_carried(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    repository = SqliteProfileRepository(connection)
    early = BASE
    late = BASE + timedelta(days=20)
    repository.save(
        Profile(
            generated_at=early,
            interests=(
                _interest("museum", 0.9, 0.80, early),
                _interest("ramen", 0.5, 0.40, early),
            ),
        )
    )
    repository.save(
        Profile(
            generated_at=late,
            interests=(
                _interest("museum", 0.9, 0.79, late),
                _interest("ramen", 0.9, 0.50, late),
            ),
        )
    )
    connection.close()
    assert main(["--data-root", str(tmp_path), "insights"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "held together" in out
    assert "museum" in out
    assert "ramen" in out
    assert main(["--data-root", str(tmp_path), "insights", "--json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed"][0]["held"] == "museum"
    assert payload["mixed"][0]["rising"] == "ramen"
