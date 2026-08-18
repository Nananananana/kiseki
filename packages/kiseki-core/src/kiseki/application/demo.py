"""A synthetic library, so the engine can be seen without a real one.

Everything here is invented: places visited on a rhythm, one the owner
has fallen out of, one within reach that never became a habit, one too
far to be a day trip, three stays captioned and read into labels, and
three profiles kept far enough apart that the trend, the lifecycle and
the comparison have something to say.

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

LAPSED = GeoPoint(35.0116, 135.7681)
"""A place with a rhythm the owner has fallen out of: four visits a
month apart, none for half a year. Without one, `kiseki suggest` has
nothing to say, and a demo whose suggestions are empty teaches nothing
about what a suggestion is."""

NEARBY = GeoPoint(34.8350, 135.4690)
"""Six kilometres out, visited twice a year ago and never since: the
shape a day trip is for -- inside the owner's own reach, and forgotten."""

DISTANT = GeoPoint(38.2680, 140.8690)
"""Four hundred kilometres away, equally forgotten, and deliberately
not offered: the reach is read from the owner's outings, not wished
for."""

READINGS = (
    ("museum", "a quiet hall of paintings"),
    ("ramen", "a bowl of ramen on a counter"),
    ("onsen", "steam over an outdoor bath"),
)

TOPICS_EARLY = (("museum", 0.9, 0.8), ("ramen", 0.5, 0.4), ("skiing", 0.6, 0.5))

TOPICS_MID = (("museum", 0.9, 0.8), ("ramen", 0.7, 0.5), ("skiing", 0.5, 0.4))
"""Skiing appears twice and then stops: seen often enough to be worth
offering back (`pick up`), which a one-off never is."""

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
    """Twelve weeks of a rhythm that leaves the house -- so the reach is a
    real distance -- and three places left behind."""
    today = _now(now)
    photographs: list[PhotoObservation] = []
    index = 0
    for week in range(12):
        visit = today - timedelta(days=7 * week)
        for offset in range(3):
            index += 1
            photographs.append(_observation(index, visit + timedelta(minutes=12 * offset), HOME))
        for offset in range(2):
            index += 1
            photographs.append(
                _observation(index, visit + timedelta(minutes=40 + 15 * offset), AWAY)
            )
    for month in range(4):
        visit = today - timedelta(days=180 + 30 * month)
        for offset in range(3):
            index += 1
            photographs.append(_observation(index, visit + timedelta(minutes=10 * offset), LAPSED))
    for number, (where, days_ago) in enumerate(((NEARBY, 300), (NEARBY, 330), (DISTANT, 400))):
        visit = today - timedelta(days=days_ago)
        for offset in range(3):
            index += 1
            photographs.append(
                _observation(index, visit + timedelta(minutes=10 * offset + number), where)
            )
    return tuple(photographs)


def _reading_photo(topic: str, today: datetime) -> PhotoId:
    """The photograph a caption describes -- one that was really seeded,
    so the reading joins the profile the way an owner's would."""
    order = [name for name, _text in READINGS].index(topic)
    return _observation(order + 1, today + timedelta(minutes=12 * order), HOME).photo_id


def demo_readings(
    now: datetime | None = None,
) -> tuple[tuple[Caption, SubjectExtraction], ...]:
    """A caption and its subjects, for each invented stay."""
    today = _now(now)
    readings: list[tuple[Caption, SubjectExtraction]] = []
    for topic, text in READINGS:
        photo = _reading_photo(topic, today)
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
