"""One reading of what a caption was about."""

from datetime import datetime, timezone

import pytest

from kiseki.domain.caption.caption import CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.photo.observation import PhotoId

WHEN = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)
KEY = CaptionKey.of([PhotoId("sha256:aa")])


class TestSubjectExtraction:
    def test_an_answer_carries_its_labels_and_model(self) -> None:
        reading = SubjectExtraction(
            key=KEY,
            labels=("ramen", "wooden counter"),
            model="qwen2.5:14b",
            created_at=WHEN,
        )
        assert reading.answered
        assert reading.labels == ("ramen", "wooden counter")

    def test_an_answer_without_labels_is_refused_construction(self) -> None:
        with pytest.raises(ValueError):
            SubjectExtraction(key=KEY, labels=(), model="m", created_at=WHEN)

    def test_a_blank_label_is_refused(self) -> None:
        with pytest.raises(ValueError):
            SubjectExtraction(key=KEY, labels=("ramen", "  "), model="m", created_at=WHEN)

    def test_a_refusal_needs_no_labels(self) -> None:
        reading = SubjectExtraction(
            key=KEY,
            labels=(),
            model="",
            created_at=WHEN,
            refused="unparseable answer",
        )
        assert not reading.answered
