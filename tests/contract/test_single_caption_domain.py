"""The single caption value: text or a recorded refusal."""

from datetime import UTC, datetime

import pytest
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.photo.observation import PhotoId

WHEN = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def test_an_answered_caption_carries_its_text():
    caption = SingleCaption(PhotoId("p1"), "a bowl of ramen", "vlm", WHEN)
    assert caption.answered
    assert caption.text == "a bowl of ramen"


def test_an_answered_caption_needs_text():
    with pytest.raises(ValueError):
        SingleCaption(PhotoId("p1"), "", "vlm", WHEN)


def test_blank_text_does_not_count_as_text():
    with pytest.raises(ValueError):
        SingleCaption(PhotoId("p1"), "   ", "vlm", WHEN)


def test_a_refusal_needs_no_text():
    caption = SingleCaption(PhotoId("p1"), "", "", WHEN, refused="too large")
    assert not caption.answered
    assert caption.refused == "too large"
