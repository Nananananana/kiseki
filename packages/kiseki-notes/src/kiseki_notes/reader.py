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
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

SUFFIXES = (".md", ".txt", ".markdown")
"""Plain text the owner wrote. Not .docx, not .pdf: a format that
needs parsing needs a library, and every library is a dependency that
reads the owner's notes.

It has a second effect that was not the reason for it. A folder
prepared by a converter usually holds its own machinery -- a manifest,
a trace map, an index -- and those are `.json`, so pointing this at
the whole of such a folder reads the writing and not the bookkeeping.
Measured on a real one: three notes either way."""

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

    The root is therefore part of the identity, and naming a different
    one re-identifies everything under it. `~/vault` and `~/vault/notes`
    give the same file two references. That is a real cost of relative
    hashing and not a bug in it: the alternative, an absolute path,
    keeps the reference stable until the folder moves and names a user
    account in the meantime.

    **How the digest is made is not a contract.** Sixteen hexadecimal
    characters, sha256, forward slashes on every platform: those are
    this producer's choices, and `docs/note-record.md` promises only
    that the reference is stable and opaque. Another library was
    measured deriving the identical sixteen characters for the same
    file, having made the same three choices independently -- an
    agreement nobody designed, nobody promised, and nothing should
    rely on. Relying on it would turn an accident into a coupling
    between two libraries that do not know about each other, and the
    day either changed its truncation the failure would arrive as
    *nothing matches* rather than as an error.
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
                day=datetime.fromtimestamp(stat.st_mtime).date(),  # noqa: DTZ006 -- `day` is local by contract
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


def busiest_day(days: Mapping[date, int]) -> tuple[date, int]:
    """The day that holds the most notes, and how many."""
    return max(days.items(), key=lambda item: (item[1], item[0]))


def looks_copied(days: Mapping[date, int]) -> bool:
    """Whether the dates look like an event rather than a history.

    A folder somebody wrote has its notes spread across the days they
    were written. More than half of everything on one calendar day is
    not writing: it is a copy without `-p`, a converter, or an unzip,
    and the day is the day that happened.

    It matters more here than it would anywhere else. A note carries no
    date of its own -- the filesystem's is the only one there is -- and
    ADR-0076 rests the whole design on it: one record is one note on one
    day, and a note returned to across six months is six records,
    because the returning is the point. Reset the timestamps and every
    trail in the folder becomes a single day.

    Never a refusal. A folder genuinely written in one sitting is
    possible, and this is a dry run for a person to read.
    """
    total = sum(days.values())
    if total < 2:
        return False
    return busiest_day(days)[1] * 2 > total
