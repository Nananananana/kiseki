"""A synthetic library, so the engine can be seen without a real one.

Everything here is invented: two places visited on a rhythm, three
stays captioned and read into labels, and three profiles kept far
enough apart that the trend, the lifecycle and the comparison have
something to say.

This module builds domain objects and nothing else. Keeping them is
the interface layer's job, because the application layer does not know
that a database exists -- the same rule the rest of the library keeps,
and the demo is not an excuse to break it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence, Profile
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint

HOME = GeoPoint(34.7810, 135.4690)
AWAY = GeoPoint(34.7050, 135.4980)

READINGS = (
    ("museum", "a quiet hall of paintings"),
    ("ramen", "a bowl of ramen on a counter"),
    ("onsen", "steam over an outdoor bath"),
)

TOPICS_EARLY = (("museum", 0.9, 0.8), ("ramen", 0.5, 0.4), ("skiing", 0.6, 0.5))
TOPICS_MID = (("museum", 0.9, 0.8), ("ramen", 0.7, 0.5))
TOPICS_LATE = (("museum", 0.9, 0.79), ("ramen", 0.9, 0.6), ("onsen", 0.8, 0.7))


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _observation(index: int, at: datetime, where: GeoPoint) -> PhotoObservation:
    return PhotoObservation(
        PhotoId(f"sha256:demo{index:04d}"),
        at,
        where,
        thumbnail_ref=f"demo/{index:04d}.jpg",
        content_kind="photo",
    )


def demo_photographs(now: datetime | None = None) -> tuple[PhotoObservation, ...]:
    """Twelve weeks of a rhythm: a place every week, another every month."""
    today = _now(now)
    photographs: list[PhotoObservation] = []
    index = 0
    for week in range(12):
        visit = today - timedelta(days=7 * week)
        for offset in range(3):
            index += 1
            photographs.append(_observation(index, visit + timedelta(minutes=12 * offset), HOME))
        if week % 4 == 0:
            for offset in range(2):
                index += 1
                photographs.append(
                    _observation(index, visit + timedelta(hours=6, minutes=15 * offset), AWAY)
                )
    return tuple(photographs)


def demo_readings(
    now: datetime | None = None,
) -> tuple[tuple[Caption, SubjectExtraction], ...]:
    """A caption and its subjects, for each invented stay."""
    today = _now(now)
    readings: list[tuple[Caption, SubjectExtraction]] = []
    for topic, text in READINGS:
        photo = PhotoId(f"sha256:demo-{topic}")
        key = CaptionKey.of([photo])
        readings.append(
            (
                Caption(
                    key=key,
                    photo_ids=(photo,),
                    text=text,
                    model="demo",
                    created_at=today,
                    prompt_version="demo/1",
                ),
                SubjectExtraction(
                    key=key,
                    labels=(topic,),
                    model="demo",
                    created_at=today,
                    prompt_version="demo/1",
                ),
            )
        )
    return tuple(readings)


def _profile(at: datetime, topics: tuple[tuple[str, float, float], ...]) -> Profile:
    interests = tuple(
        Interest(
            topic=topic,
            score=score,
            confidence=confidence,
            evidence=(
                InterestEvidence(
                    kind=EvidenceKind.PHOTOGRAPH,
                    reference=f"caption:demo-{topic}",
                    observed_at=at,
                ),
            ),
            first_seen=at,
            last_seen=at,
        )
        for topic, score, confidence in topics
    )
    return Profile(generated_at=at, interests=interests)


def demo_profiles(now: datetime | None = None) -> tuple[Profile, ...]:
    """Three readings, sixty days apart end to end."""
    today = _now(now)
    return (
        _profile(today - timedelta(days=60), TOPICS_EARLY),
        _profile(today - timedelta(days=30), TOPICS_MID),
        _profile(today, TOPICS_LATE),
    )
