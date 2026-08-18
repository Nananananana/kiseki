"""The page shows the findings, not only the measures."""

from datetime import UTC, datetime

from kiseki.domain.comparison import ChangeKind, Comparison, ComparisonEntry
from kiseki.domain.discovery import Discovery, DiscoveryFeed
from kiseki.domain.insight import (
    Insight,
    InsightDirection,
    InsightKind,
    InsightReport,
)
from kiseki.domain.interests import Profile
from kiseki.interfaces.view import render_view

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


class _Rhythm:
    def __init__(self) -> None:
        self.by_weekday = {"Mon": 1}
        self.by_month = {"2026-06": 1}


class _Report:
    def __init__(self) -> None:
        self.rhythm = _Rhythm()


def _insights() -> InsightReport:
    finding = Insight(
        topic="ramen",
        kind=InsightKind.RISING,
        direction=InsightDirection.UP,
        magnitude=0.4,
        first_seen=WHEN,
        last_seen=WHEN,
        confidence=0.6,
        evidence=("caption:aa",),
        novelty=0.7,
        derived_from=("trend",),
    )
    return InsightReport(oldest_at=WHEN, latest_at=WHEN, insights=(finding,))


def _comparison() -> Comparison:
    entry = ComparisonEntry(
        topic="museum",
        change=ChangeKind.STRONGER,
        strength_before=0.2,
        strength_after=0.45,
        evidence_before=2,
        evidence_after=4,
        evidence_refs=(),
    )
    return Comparison(before_at=WHEN, after_at=WHEN, entries=(entry,))


def _feed() -> DiscoveryFeed:
    entry = Discovery(
        topic="onsen",
        kind=InsightKind.NEW,
        magnitude=0.7,
        confidence=0.5,
        evidence=("caption:bb",),
        novelty=1.0,
        importance=0.35,
    )
    return DiscoveryFeed(oldest_at=WHEN, latest_at=WHEN, entries=(entry,))


def _render(**kwargs) -> str:
    return render_view([], _Report(), Profile(generated_at=WHEN, interests=()), None, **kwargs)


def test_the_findings_reach_the_page() -> None:
    page = _render(insights=_insights(), comparison=_comparison(), feed=_feed())
    assert "ramen" in page
    assert "museum" in page
    assert "onsen" in page
    assert "importance" in page


def test_the_numbers_travel_with_them() -> None:
    page = _render(comparison=_comparison())
    assert "0.45" in page
    assert "0.20" in page


def test_without_history_the_page_says_so() -> None:
    page = _render()
    assert page.count("not enough history") >= 3
