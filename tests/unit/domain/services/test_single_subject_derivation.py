"""Single-photo readings become interests in the shared pool (ADR-0034)."""

from datetime import UTC, datetime

import pytest
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.caption.themes import Theme
from kiseki.domain.interests import EvidenceKind
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.services.subject_interest_derivation import (
    derive_subject_interests,
)

NOW = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _photo(identifier: str, day: int, preference: bool | None = None) -> PhotoObservation:
    return PhotoObservation(
        PhotoId(identifier),
        datetime(2026, 1, day, 10, tzinfo=UTC),
        use_for_preference=preference,
    )


def _single(identifier: str) -> SingleCaption:
    return SingleCaption(PhotoId(identifier), "a scene", "vl", NOW)


def _single_reading(identifier: str, *labels: str) -> SubjectExtraction:
    return SubjectExtraction(CaptionKey.of([PhotoId(identifier)]), labels, "lm", NOW)


def _stay(identifier: str) -> Caption:
    photo_ids = (PhotoId(identifier),)
    return Caption(CaptionKey.of(photo_ids), photo_ids, "a scene", "vl", NOW)


def _stay_reading(caption: Caption, *labels: str) -> SubjectExtraction:
    return SubjectExtraction(caption.key, labels, "lm", NOW)


class TestSingleSightings:
    def test_a_single_sighting_becomes_an_interest(self) -> None:
        interests = derive_subject_interests(
            [_single_reading("sha256:aa", "ramen")],
            [],
            [_photo("sha256:aa", 5)],
            singles=[_single("sha256:aa")],
        )
        assert len(interests) == 1
        interest = interests[0]
        assert interest.topic == "ramen"
        assert interest.score == pytest.approx(1 / 3)
        assert interest.evidence[0].kind is EvidenceKind.PHOTOGRAPH
        assert interest.evidence[0].reference == "photo:sha256:aa"

    def test_singles_and_stays_pool_their_sightings(self) -> None:
        stay = _stay("sha256:aa")
        interests = derive_subject_interests(
            [_stay_reading(stay, "ramen"), _single_reading("sha256:bb", "ramen")],
            [stay],
            [_photo("sha256:aa", 1), _photo("sha256:bb", 31)],
            singles=[_single("sha256:bb")],
        )
        assert len(interests) == 1
        interest = interests[0]
        assert interest.score == pytest.approx(0.5)
        references = {evidence.reference for evidence in interest.evidence}
        assert f"caption:{stay.key.value}" in references
        assert "photo:sha256:bb" in references

    def test_a_withheld_photograph_never_becomes_evidence(self) -> None:
        interests = derive_subject_interests(
            [_single_reading("sha256:aa", "ramen")],
            [],
            [_photo("sha256:aa", 5, preference=False)],
            singles=[_single("sha256:aa")],
        )
        assert interests == ()

    def test_a_single_reading_without_its_caption_is_ignored(self) -> None:
        interests = derive_subject_interests(
            [_single_reading("sha256:aa", "ramen")],
            [],
            [_photo("sha256:aa", 5)],
        )
        assert interests == ()

    def test_a_single_whose_photograph_has_no_time_is_ignored(self) -> None:
        interests = derive_subject_interests(
            [_single_reading("sha256:aa", "ramen")],
            [],
            [],
            singles=[_single("sha256:aa")],
        )
        assert interests == ()

    def test_stay_evidence_still_points_at_captions(self) -> None:
        stay = _stay("sha256:aa")
        interest = derive_subject_interests(
            [_stay_reading(stay, "ramen")], [stay], [_photo("sha256:aa", 5)]
        )[0]
        assert interest.evidence[0].reference == f"caption:{stay.key.value}"

    def test_singles_count_toward_the_ambient_share(self) -> None:
        readings, singles, photos = [], [], []
        for index in range(8):
            identifier = f"sha256:{index:02d}"
            labels = [f"unique-{index}"]
            if index < 3:
                labels.append("building")
            readings.append(_single_reading(identifier, *labels))
            singles.append(_single(identifier))
            photos.append(_photo(identifier, index + 1))
        interests = derive_subject_interests(readings, [], photos, singles=singles)
        topics = [interest.topic for interest in interests]
        assert "building" not in topics
        assert "unique-0" in topics

    def test_a_theme_speaks_for_single_sightings_too(self) -> None:
        interests = derive_subject_interests(
            [_single_reading("sha256:aa", "ramen"), _single_reading("sha256:bb", "udon")],
            [],
            [_photo("sha256:aa", 1), _photo("sha256:bb", 2)],
            themes=[Theme(name="noodles", members=("ramen", "udon"))],
            singles=[_single("sha256:aa"), _single("sha256:bb")],
        )
        assert [interest.topic for interest in interests] == ["noodles"]
