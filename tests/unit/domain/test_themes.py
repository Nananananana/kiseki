"""Themes: labels gathered under a name, keyed by the label universe."""

from datetime import datetime, timezone

import pytest

from kiseki.domain.caption.themes import Theme, ThemeSet, ThemeSetKey

WHEN = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)


class TestThemeSetKey:
    def test_does_not_depend_on_the_order_given(self) -> None:
        assert ThemeSetKey.of(["tree", "landscape"]) == ThemeSetKey.of(["landscape", "tree"])

    def test_differs_for_a_different_universe(self) -> None:
        assert ThemeSetKey.of(["tree"]) != ThemeSetKey.of(["tree", "car"])

    def test_needs_at_least_one_label(self) -> None:
        with pytest.raises(ValueError):
            ThemeSetKey.of([])


class TestTheme:
    def test_carries_its_name_and_members(self) -> None:
        theme = Theme(name="outdoor", members=("tree", "landscape"))
        assert theme.name == "outdoor"
        assert theme.members == ("tree", "landscape")

    def test_a_single_member_is_not_a_theme(self) -> None:
        with pytest.raises(ValueError):
            Theme(name="outdoor", members=("tree",))

    def test_refuses_a_blank_name(self) -> None:
        with pytest.raises(ValueError):
            Theme(name="  ", members=("tree", "landscape"))

    def test_refuses_a_blank_member(self) -> None:
        with pytest.raises(ValueError):
            Theme(name="outdoor", members=("tree", " "))


class TestThemeSet:
    def test_may_be_empty(self) -> None:
        empty = ThemeSet(
            key=ThemeSetKey.of(["tree"]), themes=(), model="", created_at=WHEN
        )
        assert empty.themes == ()
