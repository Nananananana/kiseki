"""Finding the notes, without reading any of them."""

from datetime import date
from pathlib import Path

import pytest
from kiseki_notes.cli import EXIT_BAD_INPUT, EXIT_OK, main
from kiseki_notes.reader import find_notes, reference_for


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
