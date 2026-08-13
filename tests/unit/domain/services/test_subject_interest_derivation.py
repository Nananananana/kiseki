"""Subject readings become interests, one label at a time.

Ambient labels -- ones that appear in more than a quarter of the
readings -- describe the world the photographs were taken in, not a
choice, so they are excluded once there are enough readings to tell.
See ADR-0021.
"""

from datetime import UTC, datetime

import pytest
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.interests import EvidenceKind
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


class TestWhatBecomesAnInterest:
    def test_nothing_in_yields_nothing_out(self) -> None:
        assert derive_subject_interests([], [], []) == ()

    def test_a_label_seen_at_two_stays_becomes_one_interest(self) -> None:
        first = _caption("sha256:aa")
        second = _caption("sha256:bb")
        interests = derive_subject_interests(
            [_reading(first, "ramen"), _reading(second, "ramen")],
            [first, second],
            [_photo("sha256:aa", 1), _photo("sha256:bb", 31)],
        )
        assert len(interests) == 1
        interest = interests[0]
        assert interest.topic == "ramen"
        # score: 2 / (2 + 2); confidence: (2 / 6) * (30 / 60).
        assert interest.score == pytest.approx(0.5)
        assert interest.confidence == pytest.approx(1 / 6)
        assert interest.first_seen == datetime(2026, 1, 1, 10, tzinfo=UTC)
        assert interest.last_seen == datetime(2026, 1, 31, 10, tzinfo=UTC)

    def test_a_single_sighting_scores_but_earns_no_trust(self) -> None:
        caption = _caption("sha256:aa")
        interests = derive_subject_interests(
            [_reading(caption, "statue")], [caption], [_photo("sha256:aa", 5)]
        )
        assert interests[0].score == pytest.approx(1 / 3)
        assert interests[0].confidence == 0.0

    def test_a_refused_reading_is_ignored(self) -> None:
        caption = _caption("sha256:aa")
        refused = SubjectExtraction(caption.key, (), "", NOW, refused="unparseable")
        assert derive_subject_interests([refused], [caption], [_photo("sha256:aa", 5)]) == ()

    def test_a_reading_without_its_caption_is_ignored(self) -> None:
        caption = _caption("sha256:aa")
        assert derive_subject_interests([_reading(caption, "ramen")], [], []) == ()

    def test_a_reading_whose_photographs_have_no_time_is_ignored(self) -> None:
        caption = _caption("sha256:aa")
        interests = derive_subject_interests([_reading(caption, "ramen")], [caption], [])
        assert interests == ()


class TestNormalisation:
    def test_underscores_become_spaces(self) -> None:
        caption = _caption("sha256:aa")
        interests = derive_subject_interests(
            [_reading(caption, "dining_table")], [caption], [_photo("sha256:aa", 5)]
        )
        assert interests[0].topic == "dining table"

    def test_labels_equal_after_normalising_count_once(self) -> None:
        caption = _caption("sha256:aa")
        interests = derive_subject_interests(
            [_reading(caption, "dining_table", "dining table")],
            [caption],
            [_photo("sha256:aa", 5)],
        )
        assert len(interests) == 1
        assert len(interests[0].evidence) == 1


class TestAmbientExclusion:
    def _world(
        self, spread_label: str, spread_over: int, total: int
    ) -> tuple[list[SubjectExtraction], list[Caption], list[PhotoObservation]]:
        readings, captions, photos = [], [], []
        for index in range(total):
            caption = _caption(f"sha256:{index:02d}")
            captions.append(caption)
            photos.append(_photo(f"sha256:{index:02d}", index + 1))
            labels = [f"unique-{index}"]
            if index < spread_over:
                labels.append(spread_label)
            readings.append(_reading(caption, *labels))
        return readings, captions, photos

    def test_a_label_in_more_than_a_quarter_of_readings_is_ambient(self) -> None:
        interests = derive_subject_interests(*self._world("building", 3, 8))
        assert "building" not in [interest.topic for interest in interests]

    def test_a_label_in_exactly_a_quarter_is_kept(self) -> None:
        interests = derive_subject_interests(*self._world("statue", 2, 8))
        assert "statue" in [interest.topic for interest in interests]

    def test_the_exclusion_waits_for_enough_readings(self) -> None:
        # With two readings, every label is in at least half of them;
        # excluding on share would empty the profile.
        first = _caption("sha256:aa")
        second = _caption("sha256:bb")
        interests = derive_subject_interests(
            [_reading(first, "ramen"), _reading(second, "ramen")],
            [first, second],
            [_photo("sha256:aa", 1), _photo("sha256:bb", 2)],
        )
        assert [interest.topic for interest in interests] == ["ramen"]


class TestTheEvidence:
    def test_points_at_the_captions(self) -> None:
        caption = _caption("sha256:aa")
        interest = derive_subject_interests(
            [_reading(caption, "ramen")], [caption], [_photo("sha256:aa", 5)]
        )[0]
        assert interest.evidence[0].kind is EvidenceKind.PHOTOGRAPH
        assert interest.evidence[0].reference == f"caption:{caption.key.value}"

    def test_is_capped_at_the_ends_of_the_pattern(self) -> None:
        readings, captions, photos = [], [], []
        for index in range(12):
            caption = _caption(f"sha256:{index:02d}")
            captions.append(caption)
            photos.append(_photo(f"sha256:{index:02d}", index + 1))
            readings.append(_reading(caption, "ramen", f"unique-{index}"))
        interest = next(
            item
            for item in derive_subject_interests(readings, captions, photos)
            if item.topic == "ramen"
        )
        assert len(interest.evidence) == 10
        assert interest.evidence[0].observed_at == photos[0].captured_at
        assert interest.evidence[-1].observed_at == photos[-1].captured_at
