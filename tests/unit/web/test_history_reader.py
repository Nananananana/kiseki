"""Reading a browser history without opening a page.

Every history here is synthetic. Nothing in this suite goes near a real
browser profile, and nothing in the producer needs one: the shapes that
matter -- a locked file, a visit too short to be attention, a tab left
open overnight, a Firefox schema and a Chromium one -- are all
reproducible in a few rows.
"""

import sqlite3
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from kiseki_web.cli import EXIT_BAD_INPUT, EXIT_OK, main
from kiseki_web.reader import UnreadableHistoryError, history_in, read_window

FIREFOX_EPOCH_DIVISOR = 1_000_000
CHROMIUM_EPOCH = datetime(1601, 1, 1)

WHEN = datetime(2026, 8, 20, 10, 0, 0)


def firefox(profile: Path, visits: list[tuple[int, datetime]]) -> Path:
    """A places.sqlite with the two columns this producer reads."""
    profile.mkdir(parents=True, exist_ok=True)
    database = profile / "places.sqlite"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE moz_historyvisits (place_id INTEGER, visit_date INTEGER)")
    connection.executemany(
        "INSERT INTO moz_historyvisits VALUES (?, ?)",
        [(page, int(at.timestamp() * FIREFOX_EPOCH_DIVISOR)) for page, at in visits],
    )
    connection.commit()
    connection.close()
    return database


def chromium(profile: Path, visits: list[tuple[int, datetime, timedelta]]) -> Path:
    """A History with the duration Chromium actually records."""
    profile.mkdir(parents=True, exist_ok=True)
    database = profile / "History"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE visits (url INTEGER, visit_time INTEGER, visit_duration INT)")
    connection.executemany(
        "INSERT INTO visits VALUES (?, ?, ?)",
        [
            (
                page,
                int((at - CHROMIUM_EPOCH).total_seconds() * 1_000_000),
                int(dwell.total_seconds() * 1_000_000),
            )
            for page, at, dwell in visits
        ],
    )
    connection.commit()
    connection.close()
    return database


class TestFindingTheHistory:
    def test_firefox_is_found(self, tmp_path: Path) -> None:
        firefox(tmp_path / "p", [(1, WHEN)])
        assert history_in(tmp_path / "p").name == "places.sqlite"

    def test_chromium_is_found(self, tmp_path: Path) -> None:
        chromium(tmp_path / "p", [(1, WHEN, timedelta(minutes=1))])
        assert history_in(tmp_path / "p").name == "History"

    def test_a_directory_that_is_not_a_profile_says_so(self, tmp_path: Path) -> None:
        with pytest.raises(UnreadableHistoryError) as raised:
            history_in(tmp_path)
        assert "--profile" in str(raised.value)


class TestTheOriginalIsNeverTouched:
    def test_the_history_is_copied_and_the_original_is_unchanged(self, tmp_path: Path) -> None:
        """A producer that corrupted somebody's browser history to build
        an interest profile would deserve what was said afterwards."""
        database = firefox(tmp_path / "p", [(1, WHEN), (1, WHEN + timedelta(minutes=5))])
        before = database.read_bytes()
        read_window(database, date(2026, 8, 1), date(2026, 8, 31))
        assert database.read_bytes() == before

    def test_it_leaves_no_copy_behind(self, tmp_path: Path) -> None:
        database = firefox(tmp_path / "p", [(1, WHEN), (1, WHEN + timedelta(minutes=5))])
        read_window(database, date(2026, 8, 1), date(2026, 8, 31))
        assert sorted(p.name for p in (tmp_path / "p").iterdir()) == ["places.sqlite"]


class TestAPageOpenedIsNotAPageRead:
    def test_a_two_second_visit_is_not_attention(self, tmp_path: Path) -> None:
        database = firefox(
            tmp_path / "p",
            [(1, WHEN), (2, WHEN + timedelta(seconds=2)), (3, WHEN + timedelta(minutes=9))],
        )
        plan = read_window(database, date(2026, 8, 1), date(2026, 8, 31))
        assert len(plan.visits) == 3
        # Page 1 is the two-second visit: the next one arrived two
        # seconds later, which is what "how long it stayed" means here.
        assert [visit.page for visit in plan.kept] == [2]

    def test_a_tab_left_open_overnight_is_not_attention_either(self, tmp_path: Path) -> None:
        """The gap estimate makes an abandoned tab look like the deepest
        reading in the history, which is the more dangerous mistake: it
        arrives as a strong signal rather than a weak one."""
        database = firefox(
            tmp_path / "p",
            [(1, WHEN), (2, WHEN + timedelta(hours=14))],
        )
        plan = read_window(database, date(2026, 8, 1), date(2026, 8, 31))
        assert [visit.page for visit in plan.kept] == []

    def test_the_last_visit_has_no_next_and_so_no_dwell(self, tmp_path: Path) -> None:
        """An unknown dwell is not a long one."""
        database = firefox(tmp_path / "p", [(1, WHEN), (2, WHEN + timedelta(minutes=3))])
        plan = read_window(database, date(2026, 8, 1), date(2026, 8, 31))
        assert [visit.page for visit in plan.kept] == [1]

    def test_chromium_duration_is_used_where_it_exists(self, tmp_path: Path) -> None:
        database = chromium(
            tmp_path / "p",
            [
                (1, WHEN, timedelta(minutes=4)),
                (2, WHEN + timedelta(minutes=5), timedelta(seconds=1)),
            ],
        )
        plan = read_window(database, date(2026, 8, 1), date(2026, 8, 31))
        assert [visit.page for visit in plan.kept] == [1]


class TestTheWindow:
    def test_only_the_window_is_read(self, tmp_path: Path) -> None:
        database = firefox(
            tmp_path / "p",
            [
                (1, datetime(2026, 1, 5, 9, 0)),
                (1, datetime(2026, 1, 5, 9, 1)),
                (2, WHEN),
                (2, WHEN + timedelta(minutes=1)),
            ],
        )
        plan = read_window(database, date(2026, 8, 1), date(2026, 8, 31))
        assert {visit.page for visit in plan.visits} == {2}

    def test_pages_are_counted_once_however_often_they_are_opened(self, tmp_path: Path) -> None:
        database = firefox(
            tmp_path / "p",
            [
                (7, WHEN),
                (7, WHEN + timedelta(minutes=1)),
                (7, WHEN + timedelta(minutes=2)),
                (8, WHEN + timedelta(minutes=3)),
                (9, WHEN + timedelta(minutes=4)),
            ],
        )
        plan = read_window(database, date(2026, 8, 1), date(2026, 8, 31))
        # Four kept visits over two pages; page 9 is last and has no
        # dwell, so it is not one of them.
        assert len(plan.kept) == 4
        assert plan.pages == 2


class TestThePlan:
    def test_it_says_what_it_found(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        firefox(
            tmp_path / "p",
            [(1, WHEN), (2, WHEN + timedelta(minutes=2)), (3, WHEN + timedelta(minutes=4))],
        )
        assert (
            main(["plan", str(tmp_path / "p"), "--from", "2026-08-01", "--to", "2026-08-31"])
            == EXIT_OK
        )
        printed = capsys.readouterr().out
        assert "visits        3" in printed
        assert "attention" in printed

    def test_it_names_no_page(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Not a URL, not a title, not a host. Not even in a dry run."""
        firefox(tmp_path / "p", [(1, WHEN), (2, WHEN + timedelta(minutes=2))])
        main(["plan", str(tmp_path / "p"), "--from", "2026-08-01", "--to", "2026-08-31"])
        printed = capsys.readouterr().out
        assert "http" not in printed
        assert "no page was opened" in printed

    def test_an_empty_window_is_said_plainly(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        firefox(tmp_path / "p", [(1, WHEN)])
        assert (
            main(["plan", str(tmp_path / "p"), "--from", "2026-01-01", "--to", "2026-01-31"])
            == EXIT_OK
        )
        assert "nothing in that window" in capsys.readouterr().out

    def test_a_backwards_window_is_refused(self, tmp_path: Path) -> None:
        firefox(tmp_path / "p", [(1, WHEN)])
        result = main(["plan", str(tmp_path / "p"), "--from", "2026-08-31", "--to", "2026-08-01"])
        assert result == EXIT_BAD_INPUT

    def test_a_profile_that_is_not_one_is_refused(self, tmp_path: Path) -> None:
        assert main(["plan", str(tmp_path)]) == EXIT_BAD_INPUT


class TestADayIsLocalInBothBrowsers:
    """The contract says `day` is local. Firefox went through
    `fromtimestamp` and was; Chromium added microseconds to a naive
    1601 and stayed in UTC, so the same instant fell on different days
    depending on which browser recorded it.

    Measured on a JST machine before the fix, for one local day:

        00:00 .. 08:00 JST   firefox 09-01   chromium 08-31
        09:00 .. 23:00 JST   firefox 09-01   chromium 09-01

    Nine hours of every day, on the wrong day, for one browser only.
    The existing fixtures used 10:00 and never crossed a midnight, so
    they were green about nothing. The zone is passed explicitly here
    so this fails on a UTC runner too, where the old code happened to
    agree with itself.
    """

    JST = timezone(timedelta(hours=9))
    EARLY = datetime(2026, 9, 1, 3, 0, tzinfo=JST)
    """Three in the morning, local: the previous day in UTC."""

    def test_chromium_lands_on_the_local_day(self, tmp_path: Path) -> None:
        utc_naive = self.EARLY.astimezone(UTC).replace(tzinfo=None)
        database = chromium(tmp_path / "c", [(1, utc_naive, timedelta(seconds=30))])
        plan = read_window(database, date(2026, 9, 1), date(2026, 9, 1), zone=self.JST)
        assert [visit.day for visit in plan.visits] == [date(2026, 9, 1)], (
            "the visit was dated in UTC; the contract says local"
        )

    def test_firefox_still_lands_on_the_local_day(self, tmp_path: Path) -> None:
        database = firefox(tmp_path / "f", [(1, self.EARLY)])
        plan = read_window(database, date(2026, 9, 1), date(2026, 9, 1), zone=self.JST)
        assert [visit.day for visit in plan.visits] == [date(2026, 9, 1)]

    def test_the_same_instant_is_the_same_moment_in_both(self, tmp_path: Path) -> None:
        """Not only the day: the wall-clock time both browsers report
        for one instant must be identical, or dwell arithmetic across
        a switch of browser would be off by the zone offset."""
        utc_naive = self.EARLY.astimezone(UTC).replace(tzinfo=None)
        from_firefox = (
            read_window(
                firefox(tmp_path / "f", [(1, self.EARLY)]),
                date(2026, 9, 1),
                date(2026, 9, 1),
                zone=self.JST,
            )
            .visits[0]
            .at
        )
        from_chromium = (
            read_window(
                chromium(tmp_path / "c", [(1, utc_naive, timedelta(seconds=30))]),
                date(2026, 9, 1),
                date(2026, 9, 1),
                zone=self.JST,
            )
            .visits[0]
            .at
        )
        assert from_firefox == from_chromium == datetime(2026, 9, 1, 3, 0)
