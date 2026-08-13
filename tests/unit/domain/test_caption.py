"""A caption is keyed by the photographs it describes.

Stops are derived and replaced wholesale on every rebuild; the
photographs are content hashes and never change. A caption keyed on
them survives every rebuild that reforms the same stay. See ADR-0019.
"""

from datetime import datetime, timezone

import pytest

from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.photo.observation import PhotoId

WHEN = datetime(2026, 5, 3, 10, tzinfo=timezone.utc)


class TestCaptionKey:
    def test_does_not_depend_on_the_order_given(self) -> None:
        one = CaptionKey.of([PhotoId("sha256:aa"), PhotoId("sha256:bb")])
        other = CaptionKey.of([PhotoId("sha256:bb"), PhotoId("sha256:aa")])
        assert one == other

    def test_differs_for_a_different_set(self) -> None:
        one = CaptionKey.of([PhotoId("sha256:aa")])
        other = CaptionKey.of([PhotoId("sha256:bb")])
        assert one != other

    def test_needs_at_least_one_photograph(self) -> None:
        with pytest.raises(ValueError):
            CaptionKey.of([])


class TestCaption:
    def test_an_answer_carries_its_text_and_model(self) -> None:
        photo_ids = (PhotoId("sha256:aa"),)
        caption = Caption(
            key=CaptionKey.of(photo_ids),
            photo_ids=photo_ids,
            text="a bowl of ramen on a wooden counter",
            model="qwen3-vl:8b",
            created_at=WHEN,
        )
        assert caption.answered
        assert caption.refused is None

    def test_an_answer_without_text_is_refused_construction(self) -> None:
        photo_ids = (PhotoId("sha256:aa"),)
        with pytest.raises(ValueError):
            Caption(
                key=CaptionKey.of(photo_ids),
                photo_ids=photo_ids,
                text="   ",
                model="qwen3-vl:8b",
                created_at=WHEN,
            )

    def test_a_refusal_needs_no_text(self) -> None:
        photo_ids = (PhotoId("sha256:aa"),)
        caption = Caption(
            key=CaptionKey.of(photo_ids),
            photo_ids=photo_ids,
            text="",
            model="",
            created_at=WHEN,
            refused="image too large",
        )
        assert not caption.answered

    def test_needs_the_photographs_it_describes(self) -> None:
        with pytest.raises(ValueError):
            Caption(
                key=CaptionKey.of([PhotoId("sha256:aa")]),
                photo_ids=(),
                text="something",
                model="m",
                created_at=WHEN,
            )
