"""A label about the record is not a label about the world."""

from datetime import UTC, datetime, timedelta

from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.caption.themes import Theme
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.domain.services.generic_labels import is_generic
from kiseki.domain.services.screen_interest_derivation import (
    MIN_SCREEN_LABEL_COUNT,
    derive_screen_interests,
)
from kiseki.domain.services.subject_interest_derivation import derive_subject_interests

BASE = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _photo(name: str, days: int) -> PhotoObservation:
    return PhotoObservation(PhotoId(f"sha256:{name}"), BASE + timedelta(days=days))


def _caption(name: str) -> Caption:
    key = CaptionKey.of([PhotoId(f"sha256:{name}")])
    return Caption(
        key=key,
        photo_ids=(PhotoId(f"sha256:{name}"),),
        text="a bowl of ramen",
        model="vl",
        created_at=BASE,
    )


def _reading(name: str, labels: tuple[str, ...]) -> SubjectExtraction:
    return SubjectExtraction(
        key=CaptionKey.of([PhotoId(f"sha256:{name}")]),
        labels=labels,
        model="lm",
        created_at=BASE,
    )


def _derive(labels_by_name, themes=()):
    photos = [_photo(name, index * 10) for index, name in enumerate(labels_by_name)]
    captions = [_caption(name) for name in labels_by_name]
    readings = [_reading(name, labels) for name, labels in labels_by_name.items()]
    return derive_subject_interests(readings, captions, photos, themes=themes)


def test_the_stoplist_knows_a_record_word_from_a_world_word() -> None:
    assert is_generic("date")
    assert is_generic("  Metadata ")
    assert not is_generic("ramen")
    assert not is_generic("museum")


def test_a_generic_label_never_becomes_an_interest() -> None:
    interests = _derive({"aa": ("ramen", "date"), "bb": ("ramen", "screenshot")})
    topics = [interest.topic for interest in interests]
    assert "ramen" in topics
    assert "date" not in topics
    assert "screenshot" not in topics


def test_a_screen_reading_drops_generics_too() -> None:
    readings = tuple(
        ScreenshotReading(
            photo_id=PhotoId(f"sha256:s{index}"),
            category="map",
            labels=("route", "text"),
            model="vl",
            created_at=BASE + timedelta(days=index),
        )
        for index in range(MIN_SCREEN_LABEL_COUNT)
    )
    topics = [interest.topic for interest in derive_screen_interests(readings, BASE)]
    assert "route" in topics
    assert "text" not in topics


def test_a_theme_absorbs_the_label_that_shares_its_name() -> None:
    themes = (Theme(name="food", members=("ramen", "udon")),)
    interests = _derive(
        {
            "aa": ("ramen", "food"),
            "bb": ("udon", "food"),
            "cc": ("food",),
        },
        themes=themes,
    )
    named = [interest for interest in interests if interest.topic == "food"]
    assert len(named) == 1
    assert len(named[0].evidence) >= 3


def test_a_theme_without_a_twin_label_is_unchanged() -> None:
    themes = (Theme(name="food", members=("ramen", "udon")),)
    interests = _derive({"aa": ("ramen",), "bb": ("udon",)}, themes=themes)
    assert [interest.topic for interest in interests] == ["food"]
