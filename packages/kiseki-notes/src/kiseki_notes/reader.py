"""Finding the notes, without reading any of them.

The first thing this producer does is the thing it must be trusted
with: look at a folder the owner named and count what is there. It
opens nothing. A file's name, its size and the day it was last written
are all it takes to plan the work, and none of them travels further
than this process -- the name least of all, because
`2026-resignation.md` says as much as its contents (ADR-0075).

The folder is one the owner named. Never the home directory, never
every text file on the machine: a source that finds documents somebody
forgot they had is a search tool, and this is not one
(proposals/0009).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

SUFFIXES = (".md", ".txt", ".markdown")
"""Plain text the owner wrote. Not .docx, not .pdf: a format that
needs parsing needs a library, and every library is a dependency that
reads the owner's notes."""

SKIPPED_DIRECTORIES = (".git", ".obsidian", "node_modules", ".trash", ".venv")
"""Machinery, not writing."""

MAX_BYTES = 512 * 1024
"""A note larger than this is a data file with a .txt extension. The
limit is generous: half a megabyte is a hundred thousand words."""

REFERENCE_PREFIX = "note:"
REFERENCE_LENGTH = 16


@dataclass(frozen=True)
class FoundNote:
    """A note that exists, before anybody has read a word of it."""

    path: Path
    reference: str
    day: date
    size: int

    @property
    def too_large(self) -> bool:
        return self.size > MAX_BYTES


def reference_for(path: Path, root: Path) -> str:
    """A stable, opaque handle for a note.

    Hashed from the path relative to the folder, so the same note keeps
    its reference when the folder moves, and two people with the same
    folder layout do not collide with each other's libraries -- there
    is only ever one owner, but a reference that leaked its absolute
    path would name a user account.
    """
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    digest = hashlib.sha256(str(relative).replace("\\", "/").encode("utf-8"))
    return REFERENCE_PREFIX + digest.hexdigest()[:REFERENCE_LENGTH]


def _walk(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUFFIXES:
            continue
        if any(part in SKIPPED_DIRECTORIES for part in path.parts):
            continue
        yield path


def find_notes(root: Path) -> tuple[FoundNote, ...]:
    """Every note under the folder, with nothing opened."""
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a folder")
    found: list[FoundNote] = []
    for path in _walk(root):
        stat = path.stat()
        found.append(
            FoundNote(
                path=path,
                reference=reference_for(path, root),
                day=datetime.fromtimestamp(stat.st_mtime).date(),
                size=stat.st_size,
            )
        )
    return tuple(found)


def days_of(notes: Sequence[FoundNote]) -> dict[date, int]:
    """How many notes were last written on each day."""
    counted: dict[date, int] = {}
    for note in notes:
        counted[note.day] = counted.get(note.day, 0) + 1
    return dict(sorted(counted.items()))
