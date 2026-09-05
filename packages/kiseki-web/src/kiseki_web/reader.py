"""Looking at a browser history without opening a page.

The first thing this producer does is the thing it must be trusted
with: read a database the owner named and count what is in it. It
returns days and counts and nothing else -- no URL, no title, no host,
not even in a dry run. The contract discards them (docs/web-record.md),
and a producer that shows them while planning has shown them.

Two things are true of a browser history that are not true of a folder
of notes, and both are handled here rather than left to the caller.

**The file is locked while the browser runs.** It is copied and the
copy is read; the original is never opened for writing and never
opened at all when a copy can be made. A producer that corrupted
somebody's browser history to build an interest profile would deserve
everything said about it afterwards.

**A page opened is not a page read.** A redirect, a mis-click, a tab
that opened behind another one: all of them are visits, and none of
them is attention. The dwell floor discards them, and `plan` prints
what it discarded so the number can be argued with from the output
rather than trusted from the source.

One check the notes producer has is deliberately **not** here. It warns
when every note shares a day, because a note's day is the filesystem's
`mtime` and a copy without `-p` destroys it. A history's dates live
inside the database and survive being copied, so the same warning here
would be reasoning from the analogy rather than from the mechanism. A
browser with one day of history is a browser that is one day old.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo
from pathlib import Path

FIREFOX = "places.sqlite"
CHROMIUM = "History"

DWELL_FLOOR = timedelta(seconds=10)
"""Below this, nobody read anything.

Ten seconds is not a claim about reading speed. It is the length below
which a visit is better explained by a redirect, a mis-click or a tab
opening behind another one than by attention. The floor is the
producer's and not the contract's, because it depends on what a
browser can say."""

ABANDONED = timedelta(hours=4)
"""And above this, nobody was reading either.

A tab left open overnight looks, to a gap-to-next-visit estimate, like
the deepest attention in the history. It is the same mis-reading as the
two-second visit, at the other end, and it is the more dangerous one
because it arrives as a strong signal rather than a weak one."""


@dataclass(frozen=True)
class Visit:
    """One page, opened once. The URL is not here and never was."""

    page: int
    """The browser's own row id for the page. Local, and not a name."""

    at: datetime
    dwell: timedelta | None
    """How long it stayed, where the browser says or the gap implies."""

    @property
    def day(self) -> date:
        return self.at.date()

    @property
    def attended(self) -> bool:
        if self.dwell is None:
            return False
        return DWELL_FLOOR <= self.dwell <= ABANDONED


@dataclass(frozen=True)
class Plan:
    """What is in the window, counted."""

    visits: tuple[Visit, ...]
    kept: tuple[Visit, ...]
    pages: int
    """Distinct pages among the kept visits."""

    @property
    def discarded(self) -> int:
        return len(self.visits) - len(self.kept)

    def days(self) -> dict[date, int]:
        counted: dict[date, int] = {}
        for visit in self.kept:
            counted[visit.day] = counted.get(visit.day, 0) + 1
        return dict(sorted(counted.items()))


class UnreadableHistoryError(RuntimeError):
    """The file is not a history this producer knows how to read."""


def history_in(profile: Path) -> Path:
    """The history database inside a browser profile the owner named."""
    for name in (FIREFOX, CHROMIUM):
        candidate = profile / name
        if candidate.is_file():
            return candidate
    raise UnreadableHistoryError(
        f"no {FIREFOX} and no {CHROMIUM} under {profile}. "
        "Point --profile at a browser profile directory."
    )


WINDOWS_EPOCH_OFFSET_SECONDS = 11_644_473_600
"""Seconds from 1601-01-01 to 1970-01-01. Chromium counts from the
first, as Windows FILETIME does; everything else counts from the
second."""


def _local(seconds: float, zone: tzinfo | None) -> datetime:
    """An instant as a naive wall-clock time in `zone`, or the machine's.

    Both browsers store UTC. The contract says `day` is local, so the
    conversion happens here, once, for both -- Firefox already went
    through `fromtimestamp` and was right; Chromium added microseconds
    to a naive 1601 and stayed in UTC, so for a JST reader every visit
    between midnight and nine in the morning landed on the day before.
    Naive rather than aware because that is what `fromtimestamp` gave
    and what everything downstream expects (ADR-0064).
    """
    return datetime.fromtimestamp(seconds, tz=zone).replace(tzinfo=None)


def read_window(database: Path, since: date, until: date, zone: tzinfo | None = None) -> Plan:
    """Every visit in the window, with the ones that were not attention.

    The database is copied first. It is locked while the browser runs,
    and it is not this producer's to alter in any case.
    """
    with tempfile.TemporaryDirectory(prefix="kiseki-web-") as raw:
        copy = Path(raw) / database.name
        shutil.copy2(database, copy)
        _also_copy_journals(database, copy)
        visits = _visits_from(copy, since, until, zone)
    kept = tuple(visit for visit in visits if visit.attended)
    return Plan(visits=visits, kept=kept, pages=len({visit.page for visit in kept}))


def _also_copy_journals(database: Path, copy: Path) -> None:
    """A write-ahead log holds visits the main file does not.

    Copying the database alone loses whatever the browser has not
    checkpointed, which on a running browser is the most recent
    browsing -- exactly the part a window ending today is about.
    """
    for suffix in ("-wal", "-shm"):
        journal = database.with_name(database.name + suffix)
        if journal.is_file():
            shutil.copy2(journal, copy.with_name(copy.name + suffix))


def _visits_from(
    copy: Path, since: date, until: date, zone: tzinfo | None = None
) -> tuple[Visit, ...]:
    connection = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
        if "moz_historyvisits" in tables:
            rows = _firefox_rows(connection, zone)
        elif "visits" in tables:
            rows = _chromium_rows(connection, zone)
        else:
            raise UnreadableHistoryError(f"{copy.name} is not a Firefox or Chromium history")
    finally:
        connection.close()
    return _within(rows, since, until)


def _firefox_rows(
    connection: sqlite3.Connection, zone: tzinfo | None
) -> list[tuple[int, datetime, float | None]]:
    """Firefox records microseconds since the epoch and no duration."""
    found = connection.execute(
        "SELECT place_id, visit_date FROM moz_historyvisits ORDER BY visit_date"
    ).fetchall()
    return [(int(page), _local(int(when) / 1_000_000, zone), None) for page, when in found]


def _chromium_rows(
    connection: sqlite3.Connection, zone: tzinfo | None
) -> list[tuple[int, datetime, float | None]]:
    """Chromium counts microseconds from 1601 and records a duration."""
    found = connection.execute(
        "SELECT url, visit_time, visit_duration FROM visits ORDER BY visit_time"
    ).fetchall()
    return [
        (
            int(page),
            _local(int(when) / 1_000_000 - WINDOWS_EPOCH_OFFSET_SECONDS, zone),
            None if duration is None else float(duration),
        )
        for page, when, duration in found
    ]


def _within(
    rows: Sequence[tuple[int, datetime, float | None]], since: date, until: date
) -> tuple[Visit, ...]:
    """Trim to the window, and fill in the dwell the browser did not give.

    Where there is no duration, the gap to the next visit is the only
    estimate available. The last visit of all has no next, so it has no
    dwell and is not attention -- an unknown is not a long one.
    """
    visits: list[Visit] = []
    for index, (page, at, duration) in enumerate(rows):
        if not since <= at.date() <= until:
            continue
        if duration is not None:
            dwell: timedelta | None = timedelta(microseconds=duration)
        elif index + 1 < len(rows):
            dwell = rows[index + 1][1] - at
        else:
            dwell = None
        visits.append(Visit(page=page, at=at, dwell=dwell))
    return tuple(visits)


@dataclass(frozen=True)
class Address:
    """A page's address and title, for as long as it takes to classify.

    This is the only place either string exists, and it exists in one
    process for the length of one model call. Nothing here is returned
    to a caller that writes records, and no field of WebRecord v1 could
    hold it if it were (ADR-0085).
    """

    url: str
    title: str


def addresses_for(database: Path, pages: Sequence[int]) -> dict[int, Address]:
    """The address and title behind each page id, read from a copy.

    `plan` never calls this. Counting needs row numbers and times; only
    classifying needs to know what a page was.
    """
    if not pages:
        return {}
    wanted = set(pages)
    with tempfile.TemporaryDirectory(prefix="kiseki-web-") as raw:
        copy = Path(raw) / database.name
        shutil.copy2(database, copy)
        _also_copy_journals(database, copy)
        connection = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
        try:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
            if "moz_places" in tables:
                rows = connection.execute("SELECT id, url, title FROM moz_places").fetchall()
            elif "urls" in tables:
                rows = connection.execute("SELECT id, url, title FROM urls").fetchall()
            else:
                raise UnreadableHistoryError(f"{copy.name} holds no page table")
        finally:
            connection.close()
    return {
        int(identifier): Address(url=str(url or ""), title=str(title or ""))
        for identifier, url, title in rows
        if int(identifier) in wanted
    }
