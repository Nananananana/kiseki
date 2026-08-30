"""Classifying a page, and only then recording it.

No model is reached here. The classifier is replaced, because what is
being specified is what the producer does with an answer -- and a unit
test that reaches a model is an llm test wearing a unit test's clothes.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from kiseki_web import cli
from kiseki_web.classifier import Classification
from kiseki_web.cli import EXIT_BAD_INPUT, EXIT_OK, main

WHEN = datetime(2026, 8, 20, 10, 0, 0)

PAGES = {
    1: ("https://en.example.org/wiki/Raft_(algorithm)", "Raft (algorithm) - Example"),
    2: ("https://clinic.example.org/appointments/cancel", "Cancel your appointment"),
    3: ("https://shop.example.org/basket", "Your basket"),
}


def history(profile: Path, visits: list[tuple[int, datetime]]) -> Path:
    profile.mkdir(parents=True, exist_ok=True)
    database = profile / "places.sqlite"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE moz_historyvisits (place_id INTEGER, visit_date INTEGER)")
    connection.execute("CREATE TABLE moz_places (id INTEGER, url TEXT, title TEXT)")
    connection.executemany(
        "INSERT INTO moz_historyvisits VALUES (?, ?)",
        [(page, int(at.timestamp() * 1_000_000)) for page, at in visits],
    )
    connection.executemany(
        "INSERT INTO moz_places VALUES (?, ?, ?)",
        [(page, url, title) for page, (url, title) in PAGES.items()],
    )
    connection.commit()
    connection.close()
    return database


def a_history(root: Path) -> Path:
    """Three pages, each attended to, and one of them twice on one day."""
    return history(
        root / "p",
        [
            (1, WHEN),
            (1, WHEN + timedelta(minutes=5)),
            (2, WHEN + timedelta(minutes=10)),
            (3, WHEN + timedelta(minutes=15)),
            (1, WHEN + timedelta(minutes=20)),
        ],
    )


def answering(category: str = "reading", labels: tuple[str, ...] = ("raft",)):  # type: ignore[no-untyped-def]
    def stand_in(*_args: object, **_kwargs: object) -> Classification:
        return Classification(category=category, labels=labels, model="a stand-in")

    return stand_in


def run(root: Path, *arguments: str) -> int:
    return main(["read", str(root / "p"), "--from", "2026-08-01", "--to", "2026-08-31", *arguments])


@pytest.fixture(autouse=True)
def loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KISEKI_MODEL_HOST", "http://127.0.0.1:11434")
    monkeypatch.setattr(cli, "classify", answering())


class TestTheBoundary:
    def test_a_model_outside_it_is_refused_before_anything_is_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        a_history(tmp_path)
        monkeypatch.setenv("KISEKI_MODEL_HOST", "https://api.example.com")
        assert run(tmp_path, "--state", str(tmp_path / "state")) == EXIT_BAD_INPUT
        printed = capsys.readouterr().err
        assert "REFUSED" in printed
        assert "address and title of every page" in printed


class TestTheDryRun:
    def test_nothing_is_written_without_being_told_twice(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        a_history(tmp_path)
        assert run(tmp_path, "--state", str(tmp_path / "state")) == EXIT_OK
        assert "nothing was written" in capsys.readouterr().out
        assert not (tmp_path / "records.json").exists()

    def test_apply_without_a_destination_is_refused(self, tmp_path: Path) -> None:
        a_history(tmp_path)
        assert run(tmp_path, "--state", str(tmp_path / "state"), "--apply") == EXIT_BAD_INPUT

    def test_no_page_is_named(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """The model's host is configuration and is printed. A page's
        address is not, and neither is its title."""
        a_history(tmp_path)
        run(tmp_path, "--state", str(tmp_path / "state"))
        printed = capsys.readouterr().out
        for fragment in ("example.org", "clinic", "basket", "Raft", "wiki", "appointment"):
            assert fragment not in printed


class TestWhatWouldBeRecorded:
    def written(self, tmp_path: Path) -> list[dict[str, object]]:
        a_history(tmp_path)
        out = tmp_path / "records.json"
        assert run(tmp_path, "--state", str(tmp_path / "state"), "--apply", "--out", str(out)) == 0
        result: list[dict[str, object]] = json.loads(out.read_text(encoding="utf-8"))
        return result

    def test_it_carries_the_six_fields_and_no_others(self, tmp_path: Path) -> None:
        for record in self.written(tmp_path):
            assert set(record) == {
                "owner",
                "platform",
                "day",
                "reference",
                "category",
                "labels",
            }

    def test_it_carries_no_address_and_no_title(self, tmp_path: Path) -> None:
        text = json.dumps(self.written(tmp_path))
        for fragment in ("http", "clinic", "basket", "Raft", "wiki"):
            assert fragment not in text

    def test_one_page_on_one_day_is_one_record(self, tmp_path: Path) -> None:
        """Page 1 was opened three times in one morning."""
        records = self.written(tmp_path)
        assert len(records) == len({(r["reference"], r["day"]) for r in records})

    def test_the_reference_is_the_salted_one(self, tmp_path: Path) -> None:
        for record in self.written(tmp_path):
            assert str(record["reference"]).startswith("page:")

    def test_the_day_is_a_day(self, tmp_path: Path) -> None:
        for record in self.written(tmp_path):
            assert record["day"] == "2026-08-20"


class TestACategoryThatCarriesNoLabels:
    def test_the_category_reaches_the_record(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The stripping happens in `settle`, where the rule lives, and
        is specified there. What this pins is that the producer carries
        the settled answer rather than re-deciding it."""
        a_history(tmp_path)
        monkeypatch.setattr(cli, "classify", answering("health", ()))
        out = tmp_path / "records.json"
        run(tmp_path, "--state", str(tmp_path / "state"), "--apply", "--out", str(out))
        records = json.loads(out.read_text(encoding="utf-8"))
        assert records
        for record in records:
            assert record["category"] == "health"
            assert record["labels"] == []
