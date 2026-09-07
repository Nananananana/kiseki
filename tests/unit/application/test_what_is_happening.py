"""One screen instead of six commands (ADR-0093).

Not a shell script with better spacing: it composes values, so it can
say that one region is empty because there is nothing to say and
another because a source was never read.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from kiseki.application.limits import Limit, LimitsReport
from kiseki.application.now import (
    MOVEMENTS,
    REGIONS,
    WHAT_CHANGED,
    WHAT_IS_THIN,
    WHAT_IS_WRONG,
    WORTH_A_LOOK,
    Now,
    Region,
    what_is_happening,
)
from kiseki.application.today import OVERDUE, Today
from kiseki.domain.trends import TopicTrend, TrendDirection, TrendReport

NOW = datetime(2026, 9, 8, 9, 0, tzinfo=UTC)


def _empty_limits() -> LimitsReport:
    return LimitsReport(sources=(), limits=())


def _limits(*limits: Limit) -> LimitsReport:
    return LimitsReport(sources=(), limits=limits)


def _today() -> tuple[Today, ...]:
    return (
        Today(
            kind=OVERDUE,
            topic="place:34.70,135.50",
            why_today="645 days since you were last there",
            source="kiseki suggest",
        ),
    )


def _trends(*trends: TopicTrend) -> TrendReport:
    return TrendReport(baseline_at=NOW - timedelta(days=30), latest_at=NOW, trends=trends)


def _screen(**over: Any) -> Now:
    kwargs: dict[str, Any] = {
        "at": NOW,
        "today": (),
        "trends": None,
        "limits": _empty_limits(),
        "wrong": (),
        "photographs": 0,
        "outings": 0,
    }
    kwargs.update(over)
    return what_is_happening(**kwargs)


class TestAnEmptyRegionSaysWhy:
    """*Nothing to show* and *you have read no notes* tell a reader
    different things, and only the second is actionable."""

    def test_every_empty_region_names_something_to_run(self) -> None:
        screen = _screen()
        assert set(screen.unread) == {region.name for region in REGIONS}
        for reason in screen.unread.values():
            assert reason.strip()

    def test_a_full_region_is_not_in_unread(self) -> None:
        screen = _screen(today=_today())
        assert WORTH_A_LOOK.name not in screen.unread
        assert WHAT_CHANGED.name in screen.unread

    def test_a_region_that_cannot_say_why_is_refused(self) -> None:
        with pytest.raises(ValueError, match="blank space"):
            Region("worth a look", "   ")

    def test_worth_a_look_names_the_command_that_would_fill_it(self) -> None:
        assert "kiseki build" in WORTH_A_LOOK.empty_because
        assert "kiseki profile" in WHAT_CHANGED.empty_because

    def test_nothing_wrong_is_the_good_case_rather_than_a_missing_source(self) -> None:
        """`doctor` always runs, so an empty region here means well."""
        assert "good case" in WHAT_IS_WRONG.empty_because
        assert "good case" in WHAT_IS_THIN.empty_because


class TestWhatChanged:
    def test_a_steady_topic_is_not_a_movement(self) -> None:
        screen = _screen(
            trends=_trends(
                TopicTrend("ramen", TrendDirection.STEADY, 0.9, 0.9),
                TopicTrend("camping", TrendDirection.RISING, 0.5, 0.1),
            )
        )
        assert [trend.topic for trend in screen.changed] == ["camping"]

    def test_the_furthest_from_its_own_baseline_leads(self) -> None:
        """A topic that went from nothing to a little has moved further,
        in the only sense a screen can mean, than one already strong."""
        screen = _screen(
            trends=_trends(
                TopicTrend("strong", TrendDirection.RISING, 0.95, 0.90),
                TopicTrend("woken", TrendDirection.NEW, 0.40, 0.00),
            )
        )
        assert [trend.topic for trend in screen.changed] == ["woken", "strong"]

    def test_at_most_three_movements(self) -> None:
        screen = _screen(
            trends=_trends(
                *(
                    TopicTrend(f"topic{index}", TrendDirection.RISING, 0.9, 0.1)
                    for index in range(7)
                )
            )
        )
        assert len(screen.changed) == MOVEMENTS

    def test_a_library_with_one_reading_has_no_trend_and_says_so(self) -> None:
        """`trend` needs two kept profiles; one is not a fault."""
        screen = _screen(trends=None)
        assert screen.changed == ()
        assert WHAT_CHANGED.name in screen.unread


class TestTheWholeScreen:
    def test_a_quiet_library_says_so_rather_than_erring(self) -> None:
        assert _screen().quiet is True

    def test_one_region_filled_is_not_quiet(self) -> None:
        assert _screen(wrong=("a thumbnail is missing",)).quiet is False

    def test_the_counts_come_from_the_report_unchanged(self) -> None:
        screen = _screen(photographs=4950, outings=204)
        assert (screen.photographs, screen.outings) == (4950, 204)

    def test_what_is_thin_is_what_limits_said(self) -> None:
        limit = Limit(subject="notes", reading="none", because="nothing was read")
        assert _screen(limits=_limits(limit)).thin == (limit,)
