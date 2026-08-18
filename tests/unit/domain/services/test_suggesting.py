"""Suggestions are the owner's own evidence, pointed forward."""

from datetime import UTC, datetime, timedelta

from kiseki.domain.lifecycle import LifecycleReport, LifecycleStage, TopicLifecycle
from kiseki.domain.services.place_reading import PlaceProfile
from kiseki.domain.services.suggesting import SuggestionKind, derive_suggestions
from kiseki.domain.shared.geo import GeoPoint

TODAY = datetime(2026, 8, 1, 12, tzinfo=UTC)
KYOTO = GeoPoint(35.0116, 135.7681)


def _place(visits: int, gap: int | None, days_ago: int) -> PlaceProfile:
    last = TODAY - timedelta(days=days_ago)
    return PlaceProfile(
        centroid=KYOTO,
        visits=visits,
        first_seen=last - timedelta(days=100),
        last_seen=last,
        median_gap_days=gap,
    )


def _dormant(topic: str, seen: int, baseline: float) -> TopicLifecycle:
    return TopicLifecycle(
        topic=topic,
        stage=LifecycleStage.DORMANT,
        strength=0.0,
        seen_profiles=seen,
        baseline=baseline,
    )


def _report(*items: TopicLifecycle) -> LifecycleReport:
    return LifecycleReport(oldest_at=TODAY, latest_at=TODAY, lifecycles=tuple(items))


def test_an_overdue_place_is_suggested_with_its_numbers():
    suggestions = derive_suggestions((_place(4, 10, 44),), None, TODAY)
    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.kind is SuggestionKind.REVISIT
    assert suggestion.reference == "place:35.01160,135.76810"
    assert suggestion.days_since == 44
    assert suggestion.cadence_days == 10
    assert suggestion.confidence == 4 / 6


def test_a_fresh_place_is_left_alone():
    assert derive_suggestions((_place(4, 10, 5),), None, TODAY) == ()


def test_a_thin_place_is_left_alone():
    assert derive_suggestions((_place(2, 10, 44),), None, TODAY) == ()


def test_a_dormant_interest_is_offered_back():
    suggestions = derive_suggestions((), _report(_dormant("skiing", 4, 0.31)), TODAY)
    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.kind is SuggestionKind.REVIVE
    assert suggestion.reference == "skiing"
    assert suggestion.seen_profiles == 4
    assert suggestion.baseline == 0.31


def test_a_one_reading_wonder_is_left_alone():
    assert derive_suggestions((), _report(_dormant("skiing", 1, 0.31)), TODAY) == ()


def test_the_feed_is_capped_and_revisits_come_first():
    places = tuple(_place(4, 10, 40 + number) for number in range(4))
    report = _report(
        _dormant("skiing", 4, 0.4),
        _dormant("pottery", 3, 0.3),
    )
    suggestions = derive_suggestions(places, report, TODAY)
    assert len(suggestions) == 5
    assert suggestions[0].kind is SuggestionKind.REVISIT
    assert suggestions[-1].kind is SuggestionKind.REVIVE
