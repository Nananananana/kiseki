"""Related findings ride the answer contract; the model never sees them."""

from datetime import UTC, datetime

from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.adapters.fake.search import FakeSearchIndex
from kiseki.application.asking import ask
from kiseki.domain.insight import (
    Insight,
    InsightDirection,
    InsightKind,
    InsightReport,
)
from kiseki.interfaces.payloads import answer_payload
from kiseki.ports.search import SearchDocument

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


class StubEmbedder:
    def embed(self, texts):
        return [(1.0, 0.0) for _ in texts]

    @property
    def dimensions(self):
        return 2


def _insight(topic: str) -> Insight:
    return Insight(
        topic=topic,
        kind=InsightKind.RISING,
        direction=InsightDirection.UP,
        magnitude=0.25,
        first_seen=WHEN,
        last_seen=WHEN,
        confidence=0.5,
        evidence=("caption:aa",),
        novelty=0.7,
        derived_from=("trend", "lifecycle"),
    )


def _ask(insights=None):
    index = FakeSearchIndex()
    index.put_document(SearchDocument("stay:aa", "stay", "a bowl of ramen", WHEN))
    return ask(
        index=index,
        embedder=StubEmbedder(),
        embedding_model="m",
        language_model=FakeLanguageModel(answer=lambda system, prompt: "ramen [F1]"),
        question="ramen ?",
        insights=insights,
        now=lambda: WHEN,
    )


def test_a_matched_finding_joins_the_contract():
    report = InsightReport(
        oldest_at=WHEN,
        latest_at=WHEN,
        insights=(_insight("ramen"), _insight("skiing")),
    )
    answer = _ask(insights=report)
    assert [item.topic for item in answer.supporting_insights] == ["ramen"]


def test_the_model_never_sees_the_findings():
    report = InsightReport(oldest_at=WHEN, latest_at=WHEN, insights=(_insight("ramen"),))
    model = FakeLanguageModel(answer=lambda system, prompt: "ramen [F1]")
    index = FakeSearchIndex()
    index.put_document(SearchDocument("stay:aa", "stay", "a bowl of ramen", WHEN))
    ask(
        index=index,
        embedder=StubEmbedder(),
        embedding_model="m",
        language_model=model,
        question="ramen ?",
        insights=report,
        now=lambda: WHEN,
    )
    _system, prompt = model.seen[0]
    assert "magnitude" not in prompt
    assert "rising" not in prompt


def test_the_findings_travel_in_the_payload():
    report = InsightReport(oldest_at=WHEN, latest_at=WHEN, insights=(_insight("ramen"),))
    payload = answer_payload(_ask(insights=report))
    assert payload["supporting_insights"][0]["kind"] == "rising"
    assert payload["supporting_insights"][0]["topic"] == "ramen"
