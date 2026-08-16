"""Named places speak in the story; unnamed places stay silent."""

from datetime import UTC, datetime, timedelta

from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.narrative import narrative_facts
from kiseki.application.pipeline import Pipeline, Report
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint

WHEN = datetime(2026, 5, 3, 10, tzinfo=UTC)
LATER = datetime(2026, 6, 3, 10, tzinfo=UTC)

PLACE = "place:35.01160,135.76810"
NAMES = {PLACE: "Hirara (JP)"}


def _report() -> Report:
    return Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
    ).report()


def _interest(topic: str, score: float = 0.6, confidence: float = 0.5) -> Interest:
    evidence = (
        InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference="caption:aa", observed_at=WHEN),
    )
    return Interest(
        topic=topic,
        score=score,
        confidence=confidence,
        evidence=evidence,
        first_seen=WHEN,
        last_seen=LATER,
    )


def _profile(*interests: Interest) -> Profile:
    return Profile(generated_at=WHEN, interests=tuple(interests))


def _photo(pid: str, latitude: float, longitude: float, minutes: int = 0) -> PhotoObservation:
    return PhotoObservation(
        PhotoId(pid), WHEN + timedelta(minutes=minutes), GeoPoint(latitude, longitude)
    )


def _single(pid: str, text: str = "a bowl of ramen", refused: str | None = None) -> SingleCaption:
    return SingleCaption(PhotoId(pid), "" if refused else text, "vl", WHEN, refused=refused)


def test_a_named_place_becomes_a_fact():
    facts = narrative_facts(_profile(_interest(PLACE)), _report(), names=NAMES)
    place_facts = [fact for fact in facts if "Hirara (JP)" in fact]
    assert place_facts
    assert "sightings" in place_facts[0]


def test_unnamed_places_stay_silent():
    facts = narrative_facts(_profile(_interest(PLACE)), _report(), names={})
    assert not any("place:" in fact for fact in facts)
    assert not any("Hirara" in fact for fact in facts)


def test_nearby_singles_are_quoted():
    photos = [_photo("sha256:aa", 35.0117, 135.7681), _photo("sha256:rr", 35.0118, 135.7681, 1)]
    singles = [
        _single("sha256:aa", "a bowl of ramen at a counter"),
        _single("sha256:rr", "never quoted", refused="no thumbnail"),
    ]
    facts = narrative_facts(
        _profile(_interest(PLACE)), _report(), names=NAMES, singles=singles, photos=photos
    )
    quoted = [fact for fact in facts if fact.startswith("Near Hirara (JP)")]
    assert quoted
    assert "a bowl of ramen at a counter" in quoted[0]
    assert "never quoted" not in quoted[0]


def test_far_singles_stay_out():
    photos = [_photo("sha256:aa", 35.06, 135.7681)]
    singles = [_single("sha256:aa")]
    facts = narrative_facts(
        _profile(_interest(PLACE)), _report(), names=NAMES, singles=singles, photos=photos
    )
    assert not any(fact.startswith("Near ") for fact in facts)


def test_quotes_are_capped_and_nearest_first():
    photos = [
        _photo("sha256:01", 35.0121, 135.7681),
        _photo("sha256:02", 35.0126, 135.7681, 1),
        _photo("sha256:03", 35.0129, 135.7681, 2),
    ]
    singles = [
        _single("sha256:01", "first text"),
        _single("sha256:02", "second text"),
        _single("sha256:03", "third text"),
    ]
    facts = narrative_facts(
        _profile(_interest(PLACE)), _report(), names=NAMES, singles=singles, photos=photos
    )
    quoted = next(fact for fact in facts if fact.startswith("Near "))
    assert "first text" in quoted
    assert "second text" in quoted
    assert "third text" not in quoted


def test_place_facts_sit_between_measures_and_subjects():
    facts = narrative_facts(
        _profile(_interest(PLACE), _interest("shrine")), _report(), names=NAMES
    )
    place_at = next(index for index, fact in enumerate(facts) if "Hirara" in fact)
    subject_at = next(index for index, fact in enumerate(facts) if "shrine" in fact)
    assert place_at == 3
    assert subject_at > place_at


def test_the_model_never_sees_coordinates():
    photos = [_photo("sha256:aa", 35.0117, 135.7681)]
    facts = narrative_facts(
        _profile(_interest(PLACE)),
        _report(),
        names=NAMES,
        singles=[_single("sha256:aa")],
        photos=photos,
    )
    assert not any("place:" in fact for fact in facts)
    assert not any("35.01" in fact for fact in facts)


def test_place_facts_are_capped():
    topics = [
        "place:35.01000,135.70000",
        "place:36.01000,136.70000",
        "place:37.01000,137.70000",
        "place:38.01000,138.70000",
    ]
    names = {topic: f"Town{index} (JP)" for index, topic in enumerate(topics)}
    facts = narrative_facts(
        _profile(*[_interest(topic) for topic in topics]), _report(), names=names
    )
    assert sum(1 for fact in facts if fact.startswith("Place '")) == 3
