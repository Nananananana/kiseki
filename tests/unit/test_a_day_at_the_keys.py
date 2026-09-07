"""InputRecord v1: a day at the keys, as counts, and absent is not zero.

The rule worth reading twice is `corrections`. A recorder reading a
redacted log knows an event happened and not which key it was, so it
cannot tell a correction from any other keystroke -- not "there were
none" but "nobody could count". Reporting zero would turn the second
into the first, and no reader could tell afterwards. See ADR-0091.
"""

import json
import os
from datetime import date
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SCHEMA_VERSION, SqliteDailyInputRepository, connect
from kiseki.domain.input.daily import MAX_PLAUSIBLE_EVENTS, DailyInput
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _record(day: str = "2026-09-05", **rest: object) -> dict[str, object]:
    record: dict[str, object] = {
        "owner": "me",
        "platform": "kibi",
        "day": day,
        "active_minutes": 192,
        "events": 18060,
        "by_family": {"key": 14000, "button": 2100, "wheel": 900, "motion": 1060},
        "apps": 2,
        "corrections": 41,
    }
    record.update(rest)
    return record


def _document(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    path = tmp_path / "input-records.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def _held(tmp_path: Path) -> tuple[DailyInput, ...]:
    from kiseki.config.paths import resolve_paths

    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    return SqliteDailyInputRepository(connect(paths.db_path)).all()


class TestTheDomainValue:
    def test_a_day_holds_its_counts(self) -> None:
        day = DailyInput(
            day=date(2026, 9, 5),
            active_minutes=192,
            events=18060,
            by_family={"key": 14000},
        )
        assert day.events == 18060
        assert day.counted_corrections is False

    def test_absent_corrections_is_not_zero(self) -> None:
        """The whole point of the field being optional."""
        counted = DailyInput(
            day=date(2026, 9, 5), active_minutes=1, events=1, by_family={}, corrections=0
        )
        unknown = DailyInput(day=date(2026, 9, 5), active_minutes=1, events=1, by_family={})
        assert counted.counted_corrections is True
        assert unknown.counted_corrections is False
        assert counted.corrections == 0
        assert unknown.corrections is None

    def test_the_families_cannot_exceed_the_day(self) -> None:
        with pytest.raises(ValueError, match="more events than the day"):
            DailyInput(day=date(2026, 9, 5), active_minutes=10, events=5, by_family={"key": 6})

    def test_a_day_longer_than_a_day_is_refused(self) -> None:
        with pytest.raises(ValueError, match="between no minutes and all"):
            DailyInput(day=date(2026, 9, 5), active_minutes=1441, events=1, by_family={})

    def test_an_absurd_count_is_refused_and_an_unusual_one_is_not(self) -> None:
        """Refuse the impossible, never argue with the merely unusual."""
        DailyInput(
            day=date(2026, 9, 5),
            active_minutes=1440,
            events=MAX_PLAUSIBLE_EVENTS,
            by_family={},
        )
        with pytest.raises(ValueError, match="not a day at a keyboard"):
            DailyInput(
                day=date(2026, 9, 5),
                active_minutes=1440,
                events=MAX_PLAUSIBLE_EVENTS + 1,
                by_family={},
            )

    def test_a_negative_count_is_refused(self) -> None:
        with pytest.raises(ValueError, match="fewer than no events"):
            DailyInput(day=date(2026, 9, 5), active_minutes=1, events=-1, by_family={})


class TestTheStore:
    def test_the_schema_is_at_twelve(self, tmp_path: Path) -> None:
        connection = connect(tmp_path / "k.sqlite3")
        (version,) = connection.execute("SELECT version FROM schema_version").fetchone()
        assert version == SCHEMA_VERSION == 12

    def test_a_day_survives_the_round_trip(self, tmp_path: Path) -> None:
        connection = connect(tmp_path / "k.sqlite3")
        repository = SqliteDailyInputRepository(connection)
        day = DailyInput(
            day=date(2026, 9, 5),
            active_minutes=192,
            events=18060,
            by_family={"key": 14000, "button": 2100},
            apps=2,
            corrections=41,
        )
        repository.save_all([day])
        assert repository.all() == (day,)

    def test_an_uncounted_correction_stays_uncounted(self, tmp_path: Path) -> None:
        """Through the column and back. A NULL that came back as 0 would
        be the failure this contract exists to prevent."""
        connection = connect(tmp_path / "k.sqlite3")
        repository = SqliteDailyInputRepository(connection)
        repository.save_all(
            [DailyInput(day=date(2026, 9, 5), active_minutes=1, events=1, by_family={})]
        )
        (held,) = repository.all()
        assert held.corrections is None

    def test_the_same_day_replaces(self, tmp_path: Path) -> None:
        connection = connect(tmp_path / "k.sqlite3")
        repository = SqliteDailyInputRepository(connection)
        for events in (100, 200):
            repository.save_all(
                [
                    DailyInput(
                        day=date(2026, 9, 5),
                        active_minutes=1,
                        events=events,
                        by_family={},
                    )
                ]
            )
        assert [day.events for day in repository.all()] == [200]


class TestTheCommand:
    def test_a_document_is_taken_in(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        document = _document(tmp_path, [_record(), _record("2026-09-06")])
        assert main(["--data-root", str(tmp_path), "input", str(document)]) == EXIT_OK
        out = capsys.readouterr().out
        assert "days read     2" in out
        assert len(_held(tmp_path)) == 2

    def test_a_day_without_corrections_is_read_and_said(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A producer that could not count omits the field, and the
        command says how many of the days it read could count."""
        records = [_record(), _record("2026-09-06")]
        del records[1]["corrections"]
        document = _document(tmp_path, records)
        assert main(["--data-root", str(tmp_path), "input", str(document)]) == EXIT_OK
        assert "counted on 1 of 2" in capsys.readouterr().out
        assert sorted(day.corrections is None for day in _held(tmp_path)) == [False, True]

    def test_reading_it_again_replaces_rather_than_doubles(self, tmp_path: Path) -> None:
        document = _document(tmp_path, [_record()])
        main(["--data-root", str(tmp_path), "input", str(document)])
        main(["--data-root", str(tmp_path), "input", str(document)])
        assert len(_held(tmp_path)) == 1

    def test_a_document_that_is_not_a_list_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "wrong.json"
        path.write_text(json.dumps({"records": []}), encoding="utf-8")
        assert main(["--data-root", str(tmp_path), "input", str(path)]) == EXIT_BAD_INPUT

    def test_an_unknown_field_is_ignored_rather_than_refused(self, tmp_path: Path) -> None:
        document = _document(tmp_path, [_record(recorded_at="redacted", note="mine")])
        assert main(["--data-root", str(tmp_path), "input", str(document)]) == EXIT_OK
        assert len(_held(tmp_path)) == 1


class TestItIsAMeasureAndNotAnInterest:
    def test_a_day_at_the_keys_never_reaches_the_profile(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Fifteen thousand keystrokes is not a topic (ADR-0091). If this
        ever fails, a derivation started reading them and the decision
        needs making rather than discovering."""
        document = _document(tmp_path, [_record(), _record("2026-09-06")])
        assert main(["--data-root", str(tmp_path), "input", str(document)]) == EXIT_OK
        capsys.readouterr()
        assert main(["--data-root", str(tmp_path), "profile", "--json"]) == EXIT_OK
        out = capsys.readouterr().out
        document_text = out[out.index("{") :]
        assert json.loads(document_text)["interests"] == []

    def test_it_is_counted_by_privacy(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["--data-root", str(tmp_path), "input", str(_document(tmp_path, [_record()]))])
        capsys.readouterr()
        assert main(["--data-root", str(tmp_path), "privacy"]) == EXIT_OK
        assert "days at the keys" in capsys.readouterr().out

    def test_an_absent_source_is_a_limit(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "limits"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "input" in out
        assert "how much of your day was at the keys" in out
