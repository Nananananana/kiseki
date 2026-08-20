"""Reading a day of movement, and refusing what is not one."""

import json
import os
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqliteDailyActivityRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _write(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    path = tmp_path / "activity-records.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def _stored(tmp_path: Path):
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    return SqliteDailyActivityRepository(connect(paths.db_path)).all()


class TestActivityCommand:
    def test_days_are_read(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        path = _write(
            tmp_path,
            [
                {
                    "owner": "me",
                    "platform": "ios",
                    "day": "2026-08-18",
                    "steps": 8421,
                    "distance_m": 6180.4,
                    "floors": 12,
                },
                {"owner": "me", "platform": "ios", "day": "2026-08-19", "steps": 3007},
            ],
        )
        assert main(["--data-root", str(tmp_path), "activity", str(path)]) == EXIT_OK
        assert "days read     2" in capsys.readouterr().out
        days = _stored(tmp_path)
        assert [day.steps for day in days] == [8421, 3007]
        assert days[0].floors == 12
        assert days[1].distance_m is None

    def test_the_same_day_twice_replaces(self, tmp_path: Path) -> None:
        first = _write(
            tmp_path, [{"owner": "me", "platform": "ios", "day": "2026-08-19", "steps": 10}]
        )
        assert main(["--data-root", str(tmp_path), "activity", str(first)]) == EXIT_OK
        second = tmp_path / "again.json"
        second.write_text(
            json.dumps([{"owner": "me", "platform": "ios", "day": "2026-08-19", "steps": 20}]),
            encoding="utf-8",
        )
        assert main(["--data-root", str(tmp_path), "activity", str(second)]) == EXIT_OK
        days = _stored(tmp_path)
        assert len(days) == 1
        assert days[0].steps == 20

    def test_a_record_without_a_day_is_refused(self, tmp_path: Path) -> None:
        path = _write(tmp_path, [{"owner": "me", "platform": "ios", "steps": 10}])
        assert main(["--data-root", str(tmp_path), "activity", str(path)]) == EXIT_BAD_INPUT
        assert _stored(tmp_path) == ()

    def test_an_impossible_day_is_refused(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            [{"owner": "me", "platform": "ios", "day": "2026-08-19", "steps": 900000}],
        )
        assert main(["--data-root", str(tmp_path), "activity", str(path)]) == EXIT_BAD_INPUT

    def test_a_producer_may_carry_its_own_notes(self, tmp_path: Path) -> None:
        """Anything unknown is ignored rather than refused."""
        path = _write(
            tmp_path,
            [
                {
                    "owner": "me",
                    "platform": "ios",
                    "day": "2026-08-19",
                    "steps": 10,
                    "extra": {"source": "watch"},
                }
            ],
        )
        assert main(["--data-root", str(tmp_path), "activity", str(path)]) == EXIT_OK

    def test_a_missing_file_is_said_plainly(self, tmp_path: Path) -> None:
        assert (
            main(["--data-root", str(tmp_path), "activity", str(tmp_path / "nope.json")])
            == EXIT_BAD_INPUT
        )
