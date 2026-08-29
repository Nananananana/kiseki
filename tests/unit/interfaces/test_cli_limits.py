"""A listing shows enough to read, and says what it kept back."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqliteProfileRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence, Profile
from kiseki.interfaces.cli import DEFAULT_LIMIT, EXIT_OK, main

NOW = datetime.now(UTC)


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _interest(topic: str, at: datetime, score: float) -> Interest:
    return Interest(
        topic=topic,
        score=score,
        confidence=0.5,
        evidence=(
            InterestEvidence(
                kind=EvidenceKind.PHOTOGRAPH,
                reference=f"caption:{topic}",
                observed_at=at,
            ),
        ),
        first_seen=at,
        last_seen=at,
    )


def _seed(tmp_path: Path, topics: int = 60) -> None:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    profiles = SqliteProfileRepository(connection)
    for days in (30, 1):
        at = NOW - timedelta(days=days)
        count = topics if days == 1 else topics // 2
        profiles.save(
            Profile(
                generated_at=at,
                interests=tuple(
                    _interest(f"topic{index:03d}", at, 0.9 - index / 200) for index in range(count)
                ),
            )
        )
    connection.close()


class TestListingsAreReadable:
    def test_the_trend_shows_a_page_and_says_the_rest(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The profile is derived from evidence; the trend reads what was kept."""
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), "trend"]) == EXIT_OK
        out = capsys.readouterr().out
        assert out.count("  now ") == DEFAULT_LIMIT
        assert "--all for the rest" in out

    def test_all_shows_everything(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), "trend", "--all"]) == EXIT_OK
        out = capsys.readouterr().out
        assert out.count("  now ") > DEFAULT_LIMIT
        assert "--all for the rest" not in out

    def test_a_chosen_limit_is_kept(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), "trend", "--limit", "5"]) == EXIT_OK
        assert capsys.readouterr().out.count("  now ") == 5

    def test_a_short_listing_admits_nothing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Nothing was kept back, so nothing is said about keeping back."""
        _seed(tmp_path, topics=4)
        assert main(["--data-root", str(tmp_path), "trend"]) == EXIT_OK
        assert "--all for the rest" not in capsys.readouterr().out

    def test_the_trend_is_capped_too(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), "trend"]) == EXIT_OK
        out = capsys.readouterr().out
        assert out.count("  now ") <= DEFAULT_LIMIT

    def test_compare_is_capped_too(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), "compare"]) == EXIT_OK
        out = capsys.readouterr().out
        assert out.count("evidence ") <= DEFAULT_LIMIT

    def test_the_lifecycle_caps_each_stage(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), "lifecycle"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "per stage" in out

    def test_json_is_never_truncated(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A program is not a reader; it gets everything."""
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), "trend", "--json"]) == EXIT_OK
        out = capsys.readouterr().out
        assert out.count('"topic"') > DEFAULT_LIMIT
        assert "--all" not in out
