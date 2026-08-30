"""One name and sixteen places is not sixteen duplicates.

And sixteen places inside four kilometres is not the same thing as
seven places across twenty. Both read as "one name, N places" until the
listing says how far apart they are; measured against a real library,
both shapes are there.
"""

from dataclasses import dataclass

from kiseki.domain.shared.geo import GeoPoint
from kiseki.interfaces.naming import fold_by_name, folded_note

SOMEWHERE = GeoPoint(35.0, 135.0)
"""Where a row sits when the test is not about distance."""


@dataclass(frozen=True)
class Row:
    label: str | None
    visits: int
    centroid: GeoPoint = SOMEWHERE


def _label(row: Row) -> str | None:
    return row.label


def _point(row: Row) -> GeoPoint:
    return row.centroid


def test_the_first_of_a_name_stands_for_the_rest() -> None:
    rows = [Row("Toyonaka", 72), Row("Toyonaka", 11), Row("Umeda", 8), Row("Toyonaka", 9)]
    shown, held = fold_by_name(rows, _label)
    assert [row.visits for row in shown] == [72, 8]
    assert [row.visits for row in held[0]] == [11, 9]


def test_a_name_that_appears_once_stands_for_nothing_else() -> None:
    rows = [Row("Kyoto", 4), Row("Nara", 2)]
    shown, held = fold_by_name(rows, _label)
    assert len(shown) == 2
    assert held == {}


def test_an_unnamed_place_is_its_own() -> None:
    """Two coordinates with no name are two places, not one."""
    rows = [Row(None, 3), Row(None, 2), Row("Kyoto", 1)]
    shown, held = fold_by_name(rows, _label)
    assert len(shown) == 3
    assert held == {}


def test_the_order_given_is_the_order_kept() -> None:
    rows = [Row("Umeda", 8), Row("Toyonaka", 72), Row("Umeda", 1)]
    shown, _held = fold_by_name(rows, _label)
    assert [row.label for row in shown] == ["Umeda", "Toyonaka"]


def test_nothing_folds_to_nothing() -> None:
    shown, held = fold_by_name([], _label)
    assert shown == []
    assert held == {}


class TestHowFarApart:
    def test_a_place_that_stands_only_for_itself_says_nothing(self) -> None:
        assert folded_note([Row("Kyoto", 1)], _point) == ""

    def test_a_tight_fold_is_given_in_metres(self) -> None:
        rows = [
            Row("Toyonaka", 9, GeoPoint(34.7800, 135.4700)),
            Row("Toyonaka", 4, GeoPoint(34.7820, 135.4700)),
        ]
        note = folded_note(rows, _point)
        assert "1 more" in note
        assert "m" in note and "km" not in note

    def test_a_wide_fold_is_given_in_kilometres(self) -> None:
        rows = [
            Row("Toyonaka", 9, GeoPoint(34.7800, 135.4700)),
            Row("Toyonaka", 4, GeoPoint(34.9000, 135.4700)),
        ]
        note = folded_note(rows, _point)
        assert "1 more" in note
        assert "km" in note

    def test_the_widest_pair_is_the_one_reported(self) -> None:
        """Not the distance from the first, which understates a line of
        places running away from it."""
        rows = [
            Row("Toyonaka", 9, GeoPoint(34.8000, 135.4700)),
            Row("Toyonaka", 4, GeoPoint(34.7000, 135.4700)),
            Row("Toyonaka", 2, GeoPoint(34.9000, 135.4700)),
        ]
        note = folded_note(rows, _point)
        assert "2 more" in note
        assert "22" in note  # 0.2 degrees of latitude, not 0.1
