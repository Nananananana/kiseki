"""Finding the notes, without reading any of them."""

from datetime import date
from pathlib import Path

import pytest
from kiseki_notes.cli import EXIT_BAD_INPUT, EXIT_OK, main
from kiseki_notes.reader import busiest_day, find_notes, looks_copied, reference_for


def _write(root: Path, name: str, text: str = "hello") -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_only_plain_writing_is_found(tmp_path: Path) -> None:
    _write(tmp_path, "a.md")
    _write(tmp_path, "b.txt")
    _write(tmp_path, "c.markdown")
    _write(tmp_path, "d.pdf")
    _write(tmp_path, "e.docx")
    found = {note.path.name for note in find_notes(tmp_path)}
    assert found == {"a.md", "b.txt", "c.markdown"}


def test_machinery_is_not_writing(tmp_path: Path) -> None:
    _write(tmp_path, "notes/a.md")
    _write(tmp_path, ".git/config.txt")
    _write(tmp_path, ".obsidian/workspace.md")
    _write(tmp_path, "node_modules/readme.md")
    found = {note.path.name for note in find_notes(tmp_path)}
    assert found == {"a.md"}


def test_a_reference_is_stable_and_says_nothing(tmp_path: Path) -> None:
    path = _write(tmp_path, "diary/2026-resignation.md")
    reference = reference_for(path, tmp_path)
    assert reference.startswith("note:")
    assert "resignation" not in reference
    assert "diary" not in reference
    assert reference_for(path, tmp_path) == reference


def test_the_same_note_under_a_moved_folder_keeps_its_reference(
    tmp_path: Path,
) -> None:
    first = tmp_path / "before"
    second = tmp_path / "after"
    path_one = _write(first, "notes/a.md")
    path_two = _write(second, "notes/a.md")
    assert reference_for(path_one, first) == reference_for(path_two, second)


def test_two_notes_are_two_references(tmp_path: Path) -> None:
    one = _write(tmp_path, "a.md")
    two = _write(tmp_path, "b.md")
    assert reference_for(one, tmp_path) != reference_for(two, tmp_path)


def test_a_note_knows_the_day_it_was_written(tmp_path: Path) -> None:
    _write(tmp_path, "a.md")
    note = find_notes(tmp_path)[0]
    assert isinstance(note.day, date)


def test_a_folder_that_is_not_one_is_refused(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        find_notes(tmp_path / "nowhere")


class TestPlan:
    def test_it_counts_without_opening(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(tmp_path, "a.md", "a private thing")
        _write(tmp_path, "b.txt", "another")
        assert main(["plan", str(tmp_path)]) == EXIT_OK
        out = capsys.readouterr().out
        assert "notes         2" in out
        assert "nothing was opened" in out
        assert "a private thing" not in out

    def test_it_names_no_note(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """A file name says as much as its contents."""
        _write(tmp_path, "2026-resignation.md")
        assert main(["plan", str(tmp_path)]) == EXIT_OK
        assert "resignation" not in capsys.readouterr().out

    def test_an_empty_folder_says_so(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["plan", str(tmp_path)]) == EXIT_OK
        assert "nothing to read" in capsys.readouterr().out

    def test_a_missing_folder_is_said_plainly(self, tmp_path: Path) -> None:
        assert main(["plan", str(tmp_path / "nowhere")]) == EXIT_BAD_INPUT


class TestAFolderThatWasCopied:
    """One `cp` without -p, one converter, one unzip, and every note in
    the folder was written on the same day. NoteRecord v1 has nothing
    but the mtime to say when a note was written, and ADR-0076 rests
    the whole design on it."""

    def test_a_folder_written_over_time_is_not_remarked_on(self) -> None:
        days = {date(2026, 1, 3): 4, date(2026, 5, 9): 2, date(2026, 8, 30): 3}
        assert looks_copied(days) is False

    def test_everything_on_one_day_is(self) -> None:
        assert looks_copied({date(2026, 8, 30): 40}) is True

    def test_a_single_note_says_nothing_either_way(self) -> None:
        """One note written today is one note written today."""
        assert looks_copied({date(2026, 8, 30): 1}) is False

    def test_a_majority_on_one_day_is_enough(self) -> None:
        """A copy followed by a fortnight of writing still reads as a
        copy, and should: the fortnight is the only real history there."""
        days = {date(2026, 8, 20): 500, date(2026, 8, 29): 3, date(2026, 8, 30): 2}
        assert looks_copied(days) is True

    def test_nothing_is_not_a_copy(self) -> None:
        assert looks_copied({}) is False

    def test_the_busiest_day_is_named(self) -> None:
        days = {date(2026, 1, 3): 4, date(2026, 8, 30): 9}
        assert busiest_day(days) == (date(2026, 8, 30), 9)


def test_a_copied_folder_is_named_in_the_plan(tmp_path: Path) -> None:
    """The dry run says what it sees and refuses nothing: a folder
    genuinely written in one sitting is possible."""
    for name in ("a.md", "b.md", "c.md"):
        _write(tmp_path, name)
    result = main(["plan", str(tmp_path)])
    assert result == EXIT_OK


def test_the_plan_says_what_a_flat_folder_usually_means(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in ("a.md", "b.md", "c.md"):
        _write(tmp_path, name)
    main(["plan", str(tmp_path)])
    printed = capsys.readouterr().out
    assert "copied" in printed or "copy" in printed
    assert "-p" in printed


def test_the_command_that_would_record_it_says_so_too(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`plan` is the one people run first, and it is not the one people
    run. The dry run that classifies carries the same line.

    The model is replaced: this is about the dates, and a unit test that
    reaches a model is an llm test wearing a unit test's clothes.
    """
    from kiseki_notes import cli
    from kiseki_notes.classifier import Classification

    for name in ("a.md", "b.md", "c.md"):
        _write(tmp_path, name)
    monkeypatch.setenv("KISEKI_MODEL_HOST", "http://127.0.0.1:11434")
    monkeypatch.setattr(
        cli,
        "classify",
        lambda *_args, **_kwargs: Classification(
            category="note", labels=("a label",), model="a stand-in"
        ),
    )
    main(["read", str(tmp_path)])
    assert "copy rather than a history" in capsys.readouterr().out


def test_the_root_you_name_is_part_of_the_reference(tmp_path: Path) -> None:
    """Relative hashing keeps a reference when the folder moves, and the
    same file under two different roots is two notes. That is the cost
    of not putting an absolute path -- which would name a user account
    -- into a handle the core keeps forever."""
    note = _write(tmp_path, "vault/documents/design/gear.md")
    above = reference_for(note, tmp_path / "vault")
    inside = reference_for(note, tmp_path / "vault" / "documents")
    assert above != inside
