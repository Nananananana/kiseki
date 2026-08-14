"""Themes speak for their members.

A theme interest aggregates the sightings of its members; the members
stop speaking solo. Ambient labels stay silent even inside a theme --
ADR-0021 applies everywhere. See ADR-0024.
"""

from datetime import UTC, datetime

import pytest
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.caption.themes import Theme
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.services.subject_interest_derivation import (
    derive_subject_interests,
)

NOW = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _photo(identifier: str, day: int) -> PhotoObservation:
    return PhotoObservation(PhotoId(identifier), datetime(2026, 1, day, 10, tzinfo=UTC))


def _caption(identifier: str) -> Caption:
    photo_ids = (PhotoId(identifier),)
    return Caption(CaptionKey.of(photo_ids), photo_ids, "a scene", "vl", NOW)


def _reading(caption: Caption, *labels: str) -> SubjectExtraction:
    return SubjectExtraction(caption.key, labels, "lm", NOW)


def _outdoor_world() -> tuple[list[SubjectExtraction], list[Caption], list[PhotoObservation]]:
    # Three stays: tree at all three, landscape at the first two.
    readings, captions, photos = [], [], []
    for index, labels in enumerate([("tree", "landscape"), ("tree", "landscape"), ("tree",)]):
        caption = _caption(f"sha256:{index:02d}")
        captions.append(caption)
        photos.append(_photo(f"sha256:{index:02d}", index * 30 + 1))
        readings.append(_reading(caption, *labels))
    return readings, captions, photos


OUTDOOR = Theme(name="outdoor", members=("tree", "landscape"))


class TestThemeAbsorption:
    def test_a_theme_aggregates_and_its_members_fall_silent(self) -> None:
        readings, captions, photos = _outdoor_world()
        interests = derive_subject_interests(readings, captions, photos, themes=(OUTDOOR,))
        topics = [interest.topic for interest in interests]
        assert "outdoor" in topics
        assert "tree" not in topics
        assert "landscape" not in topics

    def test_a_shared_stay_counts_once(self) -> None:
        readings, captions, photos = _outdoor_world()
        interests = derive_subject_interests(readings, captions, photos, themes=(OUTDOOR,))
        outdoor = next(item for item in interests if item.topic == "outdoor")
        # Three distinct stays, not five sightings: score 3 / (3 + 2).
        assert outdoor.score == pytest.approx(0.6)
        assert len(outdoor.evidence) == 3

    def test_without_themes_nothing_changes(self) -> None:
        readings, captions, photos = _outdoor_world()
        topics = [
            interest.topic for interest in derive_subject_interests(readings, captions, photos)
        ]
        assert "tree" in topics
        assert "landscape" in topics

    def test_labels_outside_the_theme_still_speak(self) -> None:
        readings, captions, photos = _outdoor_world()
        extra = _caption("sha256:99")
        captions.append(extra)
        photos.append(_photo("sha256:99", 90))
        readings.append(_reading(extra, "ramen"))
        topics = [
            interest.topic
            for interest in derive_subject_interests(readings, captions, photos, themes=(OUTDOOR,))
        ]
        assert "ramen" in topics
        assert "outdoor" in topics

    def test_an_ambient_member_does_not_contribute(self) -> None:
        # Eight readings; "building" is on five of them (ambient) and
        # in a theme with "statue". The theme cannot launder building
        # back in: with one contributing member left, the theme is not
        # emitted and statue speaks solo.
        readings, captions, photos = [], [], []
        for index in range(8):
            caption = _caption(f"sha256:{index:02d}")
            captions.append(caption)
            photos.append(_photo(f"sha256:{index:02d}", index + 1))
            labels = [f"unique-{index}"]
            if index < 5:
                labels.append("building")
            if index < 2:
                labels.append("statue")
            readings.append(_reading(caption, *labels))
        laundering = Theme(name="architecture", members=("building", "statue"))
        topics = [
            interest.topic
            for interest in derive_subject_interests(
                readings, captions, photos, themes=(laundering,)
            )
        ]
        assert "architecture" not in topics
        assert "building" not in topics
        assert "statue" in topics
