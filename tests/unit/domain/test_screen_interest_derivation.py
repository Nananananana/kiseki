"""Screen readings become interests, carefully.

A label must appear on at least two screenshots to be an interest;
sensitive categories and settings screens contribute nothing; a
merged profile never overwrites what the captions already read.
See ADR-0031.
"""

from datetime import datetime, timedelta

import pytest
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.domain.services.screen_interest_derivation import (
    MIN_SCREEN_LABEL_COUNT,
    derive_screen_interests,
    merge_screen_interests,
)

AT = datetime(2026, 6, 1, 12)


def _reading(
    identifier: str,
    category: str,
    labels: tuple[str, ...],
    days: int = 0,
    refused: str | None = None,
) -> ScreenshotReading:
    return ScreenshotReading(
        photo_id=PhotoId(identifier),
        category=category,
        labels=labels if refused is None else (),
        model="m" if refused is None else "",
        created_at=AT + timedelta(days=days),
        refused=refused,
    )


def _many(label: str, count: int, category: str = "product") -> list[ScreenshotReading]:
    return [_reading(f"{label}{index}", category, (label,), days=index) for index in range(count)]


class TestDeriveScreenInterests:
    def test_nothing_from_nothing(self) -> None:
        assert derive_screen_interests((), at=AT) == ()

    def test_a_single_appearance_is_not_yet_an_interest(self) -> None:
        assert MIN_SCREEN_LABEL_COUNT == 2
        interests = derive_screen_interests(tuple(_many("camera", 1)), at=AT)
        assert interests == ()

    def test_a_repeated_label_becomes_an_interest(self) -> None:
        interests = derive_screen_interests(tuple(_many("camera", 2)), at=AT)
        (interest,) = interests
        assert interest.topic == "camera"
        assert all(e.kind is EvidenceKind.SCREENSHOT for e in interest.evidence)
        assert all(e.reference.startswith("screen:") for e in interest.evidence)

    def test_sensitive_and_settings_screens_contribute_nothing(self) -> None:
        readings = tuple(
            _many("wifi", 3, category="settings")
            + [_reading(f"c{i}", "chat", (), days=i) for i in range(3)]
        )
        assert derive_screen_interests(readings, at=AT) == ()

    def test_refusals_contribute_nothing(self) -> None:
        readings = tuple(_reading(f"r{index}", "other", (), refused="bad") for index in range(3))
        assert derive_screen_interests(readings, at=AT) == ()

    def test_the_most_seen_label_scores_highest(self) -> None:
        readings = tuple(_many("camera", 4) + _many("ramen", 2, category="food"))
        interests = {i.topic: i for i in derive_screen_interests(readings, at=AT)}
        assert interests["camera"].score > interests["ramen"].score
        assert interests["camera"].score == pytest.approx(1.0)

    def test_the_evidence_is_capped_but_counted(self) -> None:
        interests = derive_screen_interests(tuple(_many("camera", 9)), at=AT)
        (interest,) = interests
        assert len(interest.evidence) <= 5
        assert interest.first_seen == AT
        assert interest.last_seen == AT + timedelta(days=8)


class TestMergeScreenInterests:
    def _profile(self, *interests: Interest) -> Profile:
        return Profile(generated_at=AT, interests=interests)

    def _interest(self, topic: str, kind: EvidenceKind) -> Interest:
        evidence = (InterestEvidence(kind=kind, reference=f"x:{topic}", observed_at=AT),)
        return Interest(
            topic=topic,
            score=0.5,
            confidence=0.5,
            evidence=evidence,
            first_seen=AT,
            last_seen=AT,
        )

    def test_new_topics_are_appended(self) -> None:
        base = self._profile(self._interest("onsen", EvidenceKind.PHOTOGRAPH))
        merged = merge_screen_interests(base, (self._interest("camera", EvidenceKind.SCREENSHOT),))
        assert {i.topic for i in merged.interests} == {"onsen", "camera"}
        assert merged.generated_at == base.generated_at

    def test_an_existing_topic_is_not_overwritten(self) -> None:
        base = self._profile(self._interest("camera", EvidenceKind.PHOTOGRAPH))
        merged = merge_screen_interests(base, (self._interest("camera", EvidenceKind.SCREENSHOT),))
        (interest,) = merged.interests
        assert interest.evidence[0].kind is EvidenceKind.PHOTOGRAPH
