"""What a note was about -- never what it said."""

from datetime import UTC, date, datetime

import pytest
from kiseki.domain.note.reading import MAX_LABELS, NoteReading

DAY = date(2026, 8, 29)
WHEN = datetime(2026, 8, 29, 12, tzinfo=UTC)


def _reading(**changes: object) -> NoteReading:
    fields: dict[str, object] = {
        "reference": "note:9f7630c7",
        "day": DAY,
        "category": "reading",
        "labels": ("raft", "consensus"),
        "model": "demo",
        "created_at": WHEN,
    }
    fields.update(changes)
    return NoteReading(**fields)  # type: ignore[arg-type]


def test_a_reading_is_a_category_and_labels() -> None:
    reading = _reading()
    assert reading.category == "reading"
    assert reading.labels == ("raft", "consensus")
    assert reading.answered


def test_the_type_has_nowhere_to_put_the_text() -> None:
    """The rule is the shape of the type, not a pass over stored words."""
    fields = set(NoteReading.__dataclass_fields__)
    for forbidden in ("text", "body", "content", "words", "title", "path", "name"):
        assert forbidden not in fields


def test_a_diary_is_counted_and_never_labelled() -> None:
    with pytest.raises(ValueError):
        _reading(category="journal", labels=("a bad day",))
    assert _reading(category="journal", labels=()).category == "journal"


@pytest.mark.parametrize("category", ["health", "money", "people", "credential"])
def test_every_sensitive_category_refuses_labels(category: str) -> None:
    with pytest.raises(ValueError):
        _reading(category=category, labels=("anything",))


def test_a_category_nobody_defined_is_refused() -> None:
    with pytest.raises(ValueError):
        _reading(category="diary")


def test_a_refusal_needs_no_category() -> None:
    reading = _reading(category="", labels=(), refused="the model was unavailable")
    assert not reading.answered


def test_a_reading_without_a_reference_is_refused() -> None:
    with pytest.raises(ValueError):
        _reading(reference="  ")


def test_a_note_is_not_a_document_to_be_summarised() -> None:
    with pytest.raises(ValueError):
        _reading(labels=tuple(f"label{index}" for index in range(MAX_LABELS + 1)))


def test_a_blank_label_is_refused() -> None:
    with pytest.raises(ValueError):
        _reading(labels=("raft", " "))
