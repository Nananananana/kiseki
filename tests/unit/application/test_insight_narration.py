"""The findings are narrated, never added to."""

from datetime import UTC, datetime

from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.application.insight_narration import insight_facts, tell_insights
from kiseki.domain.insight import (
    Insight,
    InsightDirection,
    InsightKind,
    InsightReport,
)

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)
PLACE = "place:35.01160,135.76810"


def _insight(topic: str, kind: InsightKind = InsightKind.RETURNED, novelty: float = 0.85):
    return Insight(
        topic=topic,
        kind=kind,
        direction=InsightDirection.UP,
        magnitude=0.34,
        first_seen=WHEN,
        last_seen=WHEN,
        confidence=0.61,
        evidence=("caption:aa",),
        novelty=novelty,
        derived_from=("trend", "lifecycle"),
    )


def _report(*insights: Insight) -> InsightReport:
    return InsightReport(oldest_at=WHEN, latest_at=WHEN, insights=tuple(insights))


def test_a_finding_becomes_one_fact():
    facts = insight_facts(_report(_insight("skiing")))
    assert len(facts) == 1
    assert "skiing" in facts[0]
    assert "came back after an absence" in facts[0]
    assert "0.34" in facts[0]


def test_named_places_speak_and_bare_coordinates_stay_silent():
    facts = insight_facts(
        _report(_insight(PLACE), _insight("place:34.70000,135.50000")),
        names={PLACE: "Hirara (JP)"},
    )
    assert len(facts) == 1
    assert "Hirara (JP)" in facts[0]
    assert not any("place:" in fact for fact in facts)


def test_the_fact_list_is_capped():
    many = [_insight(f"topic{index:02d}") for index in range(12)]
    assert len(insight_facts(_report(*many))) == 8


def test_the_model_sees_numbered_facts_only():
    model = FakeLanguageModel(answer=lambda system, prompt: "a comeback [F1]")
    story = tell_insights(_report(_insight("skiing")), model, language="en")
    system, prompt = model.seen[0]
    assert "English" in system
    assert "[F1]" in prompt
    assert "skiing" in prompt
    assert story == "a comeback [F1]"


def test_no_facts_means_no_model_call():
    model = FakeLanguageModel(answer=lambda system, prompt: "never")
    story = tell_insights(_report(_insight("place:34.70000,135.50000")), model)
    assert story == ""
    assert model.seen == []
