"""The reading suites, run against what the producers actually write.

`kiseki-conformance` has **no user outside this repository**, and the
manager session measured that the family has none either. That is the
condition #368 was found under: the kit refused a byte order mark the
contract promises and the core accepts, and nobody said so for months,
because nobody runs it.

**A kit with no second program checking it is in the position of a
contract with no second implementation.** So the two producers this
repository ships are made into that second program: they are run, they
write their documents to disk, and the suites read what landed.

It is not the intended user -- that is a producer written in Swift or
Kotlin by somebody who has never read this code -- but it is a program
that is not the kit, holding the kit to its published schemas, and it
would have caught #368.

The classifier is replaced, because what is being checked is the shape
of what the producer writes and not what a model says about a note.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from kiseki_conformance import NoteRecordConformance, WebRecordConformance
from kiseki_notes import cli as notes_cli
from kiseki_notes.classifier import Classification as NoteClassification
from kiseki_web import cli as web_cli
from kiseki_web.classifier import Classification as PageClassification

WHEN = datetime(2026, 8, 20, 10, 0, 0)


def _answering(module, kind, category: str, labels: tuple[str, ...]):  # type: ignore[no-untyped-def]
    def stand_in(*_args: object, **_kwargs: object):  # type: ignore[no-untyped-def]
        return kind(category=category, labels=labels, model="a stand-in")

    return stand_in


def _a_folder(root: Path) -> Path:
    folder = root / "vault"
    folder.mkdir(parents=True)
    for name in ("raft.md", "onsen.txt", "notes.markdown"):
        (folder / name).write_text("some writing the producer will discard", encoding="utf-8")
    return folder


def _a_history(root: Path) -> Path:
    profile = root / "profile"
    profile.mkdir(parents=True)
    database = profile / "places.sqlite"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE moz_historyvisits (place_id INTEGER, visit_date INTEGER)")
    connection.execute("CREATE TABLE moz_places (id INTEGER, url TEXT, title TEXT)")
    connection.executemany(
        "INSERT INTO moz_historyvisits VALUES (?, ?)",
        [
            (1, int(WHEN.timestamp() * 1_000_000)),
            (1, int((WHEN + timedelta(minutes=5)).timestamp() * 1_000_000)),
        ],
    )
    connection.execute(
        "INSERT INTO moz_places VALUES (1, 'https://en.example.org/wiki/Raft', 'Raft')"
    )
    connection.commit()
    connection.close()
    return profile


def _note_document(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv("KISEKI_MODEL_HOST", "http://127.0.0.1:11434")
    monkeypatch.setattr(
        notes_cli, "classify", _answering(notes_cli, NoteClassification, "study", ("raft", "温泉"))
    )
    out = tmp_path / "note-records.json"
    code = notes_cli.main(["read", str(_a_folder(tmp_path)), "--apply", "--out", str(out)])
    assert code == 0, "the notes producer refused to write, so there is nothing to check"
    return json.loads(out.read_text(encoding="utf-8"))


def _page_document(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv("KISEKI_MODEL_HOST", "http://127.0.0.1:11434")
    monkeypatch.setattr(
        web_cli, "classify", _answering(web_cli, PageClassification, "reading", ("raft",))
    )
    out = tmp_path / "web-records.json"
    code = web_cli.main(
        [
            "read",
            str(_a_history(tmp_path)),
            "--from",
            "2026-08-01",
            "--to",
            "2026-08-31",
            "--apply",
            "--out",
            str(out),
            "--state",
            str(tmp_path / "s"),
        ]
    )
    assert code == 0, "the web producer refused to write, so there is nothing to check"
    return json.loads(out.read_text(encoding="utf-8"))


class TestWhatTheNotesProducerWrites(NoteRecordConformance):
    @pytest.fixture
    def document(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> object:
        return _note_document(tmp_path, monkeypatch)


class TestWhatTheWebProducerWrites(WebRecordConformance):
    @pytest.fixture
    def document(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> object:
        return _page_document(tmp_path, monkeypatch)


class TestTheTwoListsAreNotTheSameList:
    """`NoteRecord` names five categories that carry no labels and
    `WebRecord` names seven. A kit that shared one list would accept a
    web document the core refuses."""

    def a_record(self, category: str) -> list[dict[str, object]]:
        return [
            {
                "owner": "me",
                "platform": "p",
                "day": "2026-08-30",
                "reference": "x:aaaa",
                "category": category,
                "labels": ["a kettle"],
            }
        ]

    def test_shopping_with_labels_is_refused_by_the_web_contract(self) -> None:
        assert WebRecordConformance.contract.violations(self.a_record("shopping"))

    def test_and_is_not_a_note_category_at_all(self) -> None:
        """`shopping` is not in NoteRecord's list, so the note contract
        refuses it for the other reason. Both refuse; the reasons
        differ, and that is the contracts being two things."""
        assert NoteRecordConformance.contract.violations(self.a_record("shopping"))

    def test_journal_with_labels_is_refused_by_the_note_contract(self) -> None:
        assert NoteRecordConformance.contract.violations(self.a_record("journal"))

    def test_a_shared_category_carrying_labels_is_accepted_by_both(self) -> None:
        """`study` carries labels in both, so neither refuses it --
        which is what makes the refusals above mean something."""
        assert not NoteRecordConformance.contract.violations(self.a_record("study"))
        assert not WebRecordConformance.contract.violations(self.a_record("study"))
