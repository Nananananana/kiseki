"""One to three things for today, each saying why today (ADR-0092).

Not `suggest` with a limit. `suggest` ranks by how overdue a place is
and never asks whether anything happened lately; a topic that came
back after being dormant is the most interesting thing in the library
that day, and `suggest` has no idea it exists.
"""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.application.today import (
    AT_MOST,
    LATELY,
    OVERDUE,
    RECENT_DAYS,
    TURNED,
    Today,
    what_matters_today,
)
from kiseki.domain.insight import Insight, InsightDirection, InsightKind, InsightReport
from kiseki.domain.lifecycle import LifecycleReport, LifecycleStage, TopicLifecycle
from kiseki.domain.services.suggesting import Suggestion, SuggestionKind

NOW = datetime(2026, 9, 8, 9, 0, tzinfo=UTC)


def _overdue(reference: str = "place:34.70,135.50", days_since: int = 645) -> Suggestion:
    return Suggestion(
        kind=SuggestionKind.REVISIT,
        reference=reference,
        confidence=1.0,
        days_since=days_since,
        cadence_days=25,
    )


def _returned(topic: str = "camping") -> LifecycleReport:
    return LifecycleReport(
        oldest_at=NOW - timedelta(days=90),
        latest_at=NOW,
        lifecycles=(
            TopicLifecycle(
                topic=topic, stage=LifecycleStage.RETURNED, strength=0.7, seen_profiles=4
            ),
        ),
    )


def _insight(topic: str, days_ago: int, confidence: float = 0.9) -> Insight:
    return Insight(
        topic=topic,
        kind=next(iter(InsightKind)),
        direction=next(iter(InsightDirection)),
        magnitude=1.0,
        first_seen=NOW - timedelta(days=days_ago + 10),
        last_seen=NOW - timedelta(days=days_ago),
        confidence=confidence,
        evidence=("caption:a", "caption:b"),
        novelty=0.5,
        derived_from=("kiseki insights",),
    )


def _report(*insights: Insight) -> InsightReport:
    return InsightReport(oldest_at=NOW - timedelta(days=90), latest_at=NOW, insights=insights)


class TestWhatIsChosen:
    def test_an_overdue_place_says_how_long_and_how_often(self) -> None:
        (item,) = what_matters_today([_overdue()], None, None, NOW)
        assert item.kind == OVERDUE
        assert "645 days since" in item.why_today
        assert "every 25" in item.why_today
        assert item.source == "kiseki suggest"

    def test_a_topic_that_came_back_is_news(self) -> None:
        """The thing `suggest` cannot see."""
        (item,) = what_matters_today([], _returned(), None, NOW)
        assert item.kind == TURNED
        assert "came back after being dormant" in item.why_today
        assert item.source == "kiseki lifecycle"

    def test_an_insight_within_the_week_is_lately(self) -> None:
        (item,) = what_matters_today([], None, _report(_insight("ramen", 2)), NOW)
        assert item.kind == LATELY
        assert item.source == "kiseki insights"

    def test_an_insight_older_than_the_week_is_not(self) -> None:
        assert what_matters_today([], None, _report(_insight("ramen", RECENT_DAYS + 1)), NOW) == ()

    def test_an_insight_exactly_on_the_edge_is_included(self) -> None:
        """A value on the threshold belongs to the side the rule names."""
        assert len(what_matters_today([], None, _report(_insight("ramen", RECENT_DAYS)), NOW)) == 1

    def test_a_suggestion_that_is_not_a_revisit_is_left_alone(self) -> None:
        """A day trip is somewhere to go, not something that happened."""
        trip = Suggestion(
            kind=SuggestionKind.DAY_TRIP,
            reference="place:35.12,135.76",
            confidence=0.2,
            days_since=700,
            distance_km=45.0,
        )
        assert what_matters_today([trip], None, None, NOW) == ()


class TestTheOrder:
    def test_overdue_comes_before_turned_before_lately(self) -> None:
        """Fixed and stated rather than computed from scores that were
        never comparable."""
        items = what_matters_today([_overdue()], _returned(), _report(_insight("ramen", 1)), NOW)
        assert [item.kind for item in items] == [OVERDUE, TURNED, LATELY]

    def test_at_most_three(self) -> None:
        items = what_matters_today(
            [_overdue(f"place:{index},0", 600 + index) for index in range(9)],
            _returned(),
            _report(_insight("ramen", 1)),
            NOW,
        )
        assert len(items) == AT_MOST

    def test_one_topic_appears_once(self) -> None:
        """A topic that is both returned and lately is one card, not two."""
        items = what_matters_today([], _returned("camping"), _report(_insight("camping", 1)), NOW)
        assert [item.topic for item in items] == ["camping"]

    def test_the_freshest_insight_leads_its_group(self) -> None:
        items = what_matters_today(
            [], None, _report(_insight("quiet", 1, 0.2), _insight("loud", 1, 0.95)), NOW
        )
        assert [item.topic for item in items] == ["loud", "quiet"]


class TestNothingToSay:
    def test_an_empty_library_says_nothing_rather_than_inventing(self) -> None:
        assert what_matters_today([], None, None, NOW) == ()

    def test_a_reason_is_not_optional(self) -> None:
        with pytest.raises(ValueError, match="menu entry"):
            Today(kind=OVERDUE, topic="a", why_today="   ", source="kiseki suggest")

    def test_a_kind_nobody_decided_about_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not a reason for today"):
            Today(kind="vibes", topic="a", why_today="because", source="kiseki suggest")
