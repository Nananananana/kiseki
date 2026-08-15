"""The indexing run: sync documents, embed what lacks a vector."""

from datetime import UTC, datetime, timedelta

from kiseki.adapters.fake.models import FakeTextEmbedder
from kiseki.adapters.fake.search import FakeSearchIndex
from kiseki.application.indexing import run_indexing
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.ports.models import ModelUnavailableError

NOW = datetime(2026, 6, 1, 12, tzinfo=UTC)
START = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)


def _photo(pid: str, minutes: int = 0, preference: bool | None = None) -> PhotoObservation:
    return PhotoObservation(
        PhotoId(pid),
        START + timedelta(minutes=minutes),
        None,
        use_for_preference=preference,
    )


def _stay(*pids: str, text: str = "a stone temple gate") -> Caption:
    photo_ids = tuple(PhotoId(pid) for pid in pids)
    return Caption(CaptionKey.of(photo_ids), photo_ids, text, "vl", NOW)


def _single(pid: str, text: str = "a bowl of ramen", refused: str | None = None) -> SingleCaption:
    return SingleCaption(PhotoId(pid), "" if refused else text, "vl", NOW, refused=refused)


def _screen(pid: str, category: str = "food", labels: tuple = ("ramen",)) -> ScreenshotReading:
    return ScreenshotReading(PhotoId(pid), category, labels, "vlm", NOW)


class StubRepo:
    def __init__(self, items=()):
        self._items = tuple(items)

    def all(self):
        return self._items


class UnavailableEmbedder:
    def embed(self, texts):
        raise ModelUnavailableError("away")

    @property
    def dimensions(self):
        return 8


def _run(photos, captions=(), singles=(), screens=(), index=None, embedder=None, **kwargs):
    kept = index if index is not None else FakeSearchIndex()
    report = run_indexing(
        photos=StubRepo(photos),
        captions=StubRepo(captions),
        singles=StubRepo(singles),
        screens=StubRepo(screens),
        index=kept,
        embedder=embedder if embedder is not None else FakeTextEmbedder(),
        embedding_model=kwargs.pop("embedding_model", "fake"),
        **kwargs,
    )
    return report, kept


def test_a_stay_caption_becomes_a_document():
    stay = _stay("sha256:aa", "sha256:bb")
    report, index = _run([_photo("sha256:aa", 10), _photo("sha256:bb", 0)], captions=[stay])
    assert report.documents_added == 1
    assert index.has_document(f"stay:{stay.key.value}")
    assert report.embedded == 1


def test_singles_and_screens_join_the_corpus():
    report, index = _run(
        [_photo("sha256:aa"), _photo("sha256:bb", 1)],
        singles=[_single("sha256:aa")],
        screens=[_screen("sha256:bb", labels=("ramen", "bowl"))],
    )
    assert report.documents_total == 2
    assert index.has_document("single:sha256:aa")
    assert index.has_document("screen:sha256:bb")
    screen_doc = next(
        document
        for document in index.missing_embeddings("other")
        if document.doc_key == "screen:sha256:bb"
    )
    assert "food" in screen_doc.text
    assert "ramen" in screen_doc.text


def test_refusals_and_unlabelled_screens_are_left_out():
    report, _index = _run(
        [_photo("sha256:aa"), _photo("sha256:bb", 1)],
        singles=[_single("sha256:aa", refused="no thumbnail")],
        screens=[_screen("sha256:bb", category="chat", labels=())],
    )
    assert report.documents_total == 0


def test_withheld_photographs_are_never_indexed():
    report, _index = _run(
        [_photo("sha256:aa", preference=False)],
        singles=[_single("sha256:aa")],
    )
    assert report.documents_total == 0


def test_a_second_run_adds_and_embeds_nothing():
    photos = [_photo("sha256:aa")]
    singles = [_single("sha256:aa")]
    index = FakeSearchIndex()
    first, _ = _run(photos, singles=singles, index=index)
    second, _ = _run(photos, singles=singles, index=index)
    assert first.embedded == 1
    assert second.documents_added == 0
    assert second.embedded == 0
    assert second.already_embedded == 1


def test_an_unavailable_embedder_pauses_the_run():
    report, _index = _run(
        [_photo("sha256:aa")],
        singles=[_single("sha256:aa")],
        embedder=UnavailableEmbedder(),
    )
    assert report.paused
    assert report.embedded == 0
    assert report.documents_added == 1


def test_the_limit_bounds_the_embedding_work():
    photos = [_photo("sha256:aa"), _photo("sha256:bb", 1), _photo("sha256:cc", 2)]
    singles = [_single("sha256:aa"), _single("sha256:bb"), _single("sha256:cc")]
    index = FakeSearchIndex()
    first, _ = _run(photos, singles=singles, index=index, limit=1)
    second, _ = _run(photos, singles=singles, index=index)
    assert first.embedded == 1
    assert second.already_embedded == 1
    assert second.embedded == 2


def test_vectors_are_kept_per_model():
    photos = [_photo("sha256:aa")]
    singles = [_single("sha256:aa")]
    index = FakeSearchIndex()
    _run(photos, singles=singles, index=index, embedding_model="a")
    _run(photos, singles=singles, index=index, embedding_model="b")
    assert index.embedding_count("a") == 1
    assert index.embedding_count("b") == 1
