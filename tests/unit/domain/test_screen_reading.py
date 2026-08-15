"""A screen reading keeps a category and labels, never the words.

The raw text of a screenshot has no field to live in -- that is the
Privacy Filter, enforced by the type rather than by discipline. The
sensitive categories never carry labels at all. See ADR-0030.
"""

from datetime import datetime

import pytest
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.screen.reading import (
    CATEGORIES,
    SENSITIVE_CATEGORIES,
    ScreenshotReading,
)

AT = datetime(2026, 6, 1, 12)


def _reading(category: str, labels: tuple[str, ...]) -> ScreenshotReading:
    return ScreenshotReading(
        photo_id=PhotoId("p1"),
        category=category,
        labels=labels,
        model="m",
        created_at=AT,
    )


class TestScreenshotReading:
    def test_a_sensitive_category_never_carries_labels(self) -> None:
        assert "chat" in SENSITIVE_CATEGORIES
        with pytest.raises(ValueError):
            _reading("chat", ("gossip",))
        assert _reading("chat", ()).answered

    def test_an_answer_needs_a_known_category(self) -> None:
        assert "product" in CATEGORIES
        with pytest.raises(ValueError):
            _reading("horoscope", ())

    def test_a_refusal_is_not_an_answer(self) -> None:
        refusal = ScreenshotReading(
            photo_id=PhotoId("p1"),
            category="other",
            labels=(),
            model="",
            created_at=AT,
            refused="unparseable",
        )
        assert not refusal.answered
