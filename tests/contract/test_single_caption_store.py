"""The single-caption stores, fake and sqlite, held to one contract."""

from datetime import UTC, datetime

import pytest
from kiseki.adapters.fake.singles import FakeSingleCaptionRepository
from kiseki.adapters.sqlite.store import SqliteSingleCaptionRepository, connect
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.photo.observation import PhotoId

WHEN = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


@pytest.fixture(params=["fake", "sqlite"])
def repository(request, tmp_path):
    if request.param == "fake":
        return FakeSingleCaptionRepository()
    connection = connect(tmp_path / "store.sqlite3")
    request.addfinalizer(connection.close)
    return SqliteSingleCaptionRepository(connection)


def test_an_absent_photograph_answers_none(repository):
    assert repository.get(PhotoId("missing")) is None


def test_a_saved_caption_is_found_again(repository):
    caption = SingleCaption(PhotoId("p1"), "a bowl of ramen", "vlm", WHEN)
    repository.save(caption)
    assert repository.get(PhotoId("p1")) == caption


def test_saving_again_replaces_the_caption(repository):
    repository.save(SingleCaption(PhotoId("p1"), "first", "vlm", WHEN))
    repository.save(SingleCaption(PhotoId("p1"), "second", "vlm", WHEN))
    found = repository.get(PhotoId("p1"))
    assert found is not None
    assert found.text == "second"


def test_all_answers_in_the_order_saved(repository):
    repository.save(SingleCaption(PhotoId("p1"), "one", "vlm", WHEN))
    repository.save(SingleCaption(PhotoId("p2"), "two", "vlm", WHEN))
    assert [c.photo_id.value for c in repository.all()] == ["p1", "p2"]


def test_a_refusal_round_trips(repository):
    repository.save(SingleCaption(PhotoId("p1"), "", "", WHEN, refused="too large"))
    found = repository.get(PhotoId("p1"))
    assert found is not None
    assert not found.answered
    assert found.refused == "too large"
