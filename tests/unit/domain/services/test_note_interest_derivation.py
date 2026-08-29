"""Note readings become interests, carefully."""

from datetime import UTC, date, datetime

from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.note.reading import NoteReading
from kiseki.domain.services.note_interest_derivation import (
    MIN_NOTE_DAYS,
    derive_note_interests,
    merge_note_interests,
)

WHEN = datetime(2026, 8, 29, 12, tzinfo=UTC)


def _reading(
    reference: str,
    day: date,
    labels: tuple[str, ...],
    category: str = "reading",
    refused: str | None = None,
) -> NoteReading:
    return NoteReading(
        reference=reference,
        day=day,
        category=category,
        labels=labels,
        model="demo",
        created_at=WHEN,
        refused=refused,
    )


def test_a_word_written_once_is_a_passing_thought() -> None:
    readings = [_reading("note:a", date(2026, 3, 1), ("raft",))]
    assert derive_note_interests(readings) == ()


def test_a_word_written_on_two_days_is_a_subject() -> None:
    readings = [
        _reading("note:a", date(2026, 3, 1), ("raft",)),
        _reading("note:a", date(2026, 5, 14), ("raft", "consensus")),
    ]
    interests = derive_note_interests(readings)
    assert [interest.topic for interest in interests] == ["raft"]
    assert interests[0].evidence[0].kind is EvidenceKind.NOTE


def test_two_notes_on_one_day_are_still_one_day() -> None:
    """The threshold counts days, not files, because a sitting is a day."""
    readings = [
        _reading("note:a", date(2026, 3, 1), ("raft",)),
        _reading("note:b", date(2026, 3, 1), ("raft",)),
    ]
    assert derive_note_interests(readings) == ()


def test_a_sensitive_category_contributes_nothing() -> None:
    """It carries no labels either; this is the second lock."""
    readings = [
        _reading("note:a", date(2026, 3, 1), (), category="journal"),
        _reading("note:a", date(2026, 5, 14), (), category="journal"),
    ]
    assert derive_note_interests(readings) == ()


def test_a_refused_reading_says_nothing() -> None:
    readings = [
        _reading("note:a", date(2026, 3, 1), ("raft",), refused="no JSON"),
        _reading("note:a", date(2026, 5, 14), ("raft",), refused="no JSON"),
    ]
    assert derive_note_interests(readings) == ()


def test_a_label_about_the_record_is_left_out() -> None:
    readings = [
        _reading("note:a", date(2026, 3, 1), ("document", "raft")),
        _reading("note:a", date(2026, 5, 14), ("document", "raft")),
    ]
    assert [interest.topic for interest in derive_note_interests(readings)] == ["raft"]


def test_the_evidence_points_at_the_note_and_not_at_its_words() -> None:
    readings = [
        _reading("note:9f76", date(2026, 3, 1), ("raft",)),
        _reading("note:9f76", date(2026, 5, 14), ("raft",)),
    ]
    reference = derive_note_interests(readings)[0].evidence[0].reference
    assert reference == "note:9f76"


def test_the_photographs_keep_their_reading() -> None:
    """A photograph of a thing outweighs a word in a file about it."""
    from_photos = Profile(
        generated_at=WHEN,
        interests=(
            Interest(
                topic="raft",
                score=0.9,
                confidence=0.8,
                evidence=(
                    InterestEvidence(
                        kind=EvidenceKind.PHOTOGRAPH,
                        reference="caption:aaaa",
                        observed_at=WHEN,
                    ),
                ),
                first_seen=WHEN,
                last_seen=WHEN,
            ),
        ),
    )
    readings = [
        _reading("note:a", date(2026, 3, 1), ("raft", "consensus")),
        _reading("note:a", date(2026, 5, 14), ("raft", "consensus")),
    ]
    merged = merge_note_interests(from_photos, derive_note_interests(readings))
    topics = [interest.topic for interest in merged.interests]
    assert topics.count("raft") == 1
    assert "consensus" in topics
    assert merged.interests[0].evidence[0].kind is EvidenceKind.PHOTOGRAPH


def test_nothing_to_merge_changes_nothing() -> None:
    profile = Profile(generated_at=WHEN, interests=())
    assert merge_note_interests(profile, ()) is profile


def test_the_threshold_is_where_it_says_it_is() -> None:
    days = [date(2026, 3, index + 1) for index in range(MIN_NOTE_DAYS)]
    readings = [_reading("note:a", day, ("raft",)) for day in days]
    assert len(derive_note_interests(readings)) == 1
