"""A place condition filters evidence the way a time window does."""

from datetime import UTC, datetime

from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.adapters.fake.search import FakeSearchIndex
from kiseki.application.asking import ask
from kiseki.domain.shared.geo import GeoPoint
from kiseki.ports.search import SearchDocument

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)
KYOTO = GeoPoint(35.0116, 135.7681)
OSAKA = GeoPoint(34.6937, 135.5023)


class StubEmbedder:
    def embed(self, texts):
        return [(1.0, 0.0) for _ in texts]

    @property
    def dimensions(self):
        return 2


def _ask(index, model, **kwargs):
    return ask(
        index=index,
        embedder=StubEmbedder(),
        embedding_model="m",
        language_model=model,
        question="ramen ?",
        now=lambda: WHEN,
        **kwargs,
    )


def _index() -> FakeSearchIndex:
    index = FakeSearchIndex()
    index.put_document(SearchDocument("stay:aa", "stay", "a bowl of ramen", WHEN))
    index.put_document(SearchDocument("stay:bb", "stay", "ramen at a counter", WHEN))
    return index


def test_far_evidence_drops_when_near_is_given():
    model = FakeLanguageModel(answer=lambda system, prompt: "ramen [F1]")
    answer = _ask(
        _index(),
        model,
        near=KYOTO,
        locations={"stay:aa": KYOTO, "stay:bb": OSAKA},
    )
    assert len(answer.evidence) == 1
    assert answer.evidence[0].document.doc_key == "stay:aa"


def test_evidence_without_a_location_never_matches_a_place():
    model = FakeLanguageModel(answer=lambda system, prompt: "ramen [F1]")
    answer = _ask(_index(), model, near=KYOTO, locations={"stay:aa": KYOTO})
    assert [item.document.doc_key for item in answer.evidence] == ["stay:aa"]


def test_without_near_nothing_is_filtered():
    model = FakeLanguageModel(answer=lambda system, prompt: "ramen [F1][F2]")
    answer = _ask(_index(), model, locations={"stay:aa": KYOTO})
    assert len(answer.evidence) == 2
