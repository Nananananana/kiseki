"""An excluded reading never returns as answer evidence."""

from datetime import UTC, datetime

from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.adapters.fake.search import FakeSearchIndex
from kiseki.application.asking import ask
from kiseki.ports.search import SearchDocument

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


class StubEmbedder:
    def embed(self, texts):
        return [(1.0, 0.0) for _ in texts]

    @property
    def dimensions(self):
        return 2


def _ask(index, model, excluded=frozenset()):
    return ask(
        index=index,
        embedder=StubEmbedder(),
        embedding_model="m",
        language_model=model,
        question="ramen ?",
        excluded=excluded,
        now=lambda: WHEN,
    )


def test_an_excluded_caption_drops_from_the_evidence():
    index = FakeSearchIndex()
    index.put_document(SearchDocument("stay:aa", "stay", "a bowl of ramen", WHEN))
    index.put_document(SearchDocument("stay:bb", "stay", "ramen at a counter", WHEN))
    model = FakeLanguageModel(answer=lambda system, prompt: "ramen [F1]")
    answer = _ask(index, model, excluded=frozenset({"caption:aa"}))
    assert len(answer.evidence) == 1
    _system, prompt = model.seen[0]
    assert "a bowl of ramen" not in prompt
    assert "ramen at a counter" in prompt


def test_a_corrected_photo_maps_to_its_single_document():
    index = FakeSearchIndex()
    index.put_document(SearchDocument("single:pp", "single", "a bowl of ramen", WHEN))
    model = FakeLanguageModel(answer=lambda system, prompt: "never")
    answer = _ask(index, model, excluded=frozenset({"photo:pp"}))
    assert answer.evidence == ()


def test_everything_excluded_means_no_model_call():
    index = FakeSearchIndex()
    index.put_document(SearchDocument("stay:aa", "stay", "a bowl of ramen", WHEN))
    model = FakeLanguageModel(answer=lambda system, prompt: "never")
    answer = _ask(index, model, excluded=frozenset({"caption:aa"}))
    assert answer.evidence == ()
    assert answer.confidence == 0.0
    assert model.seen == []
