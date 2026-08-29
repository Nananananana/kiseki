"""One name and sixteen places is not sixteen duplicates."""

from dataclasses import dataclass

from kiseki.interfaces.naming import fold_by_name


@dataclass(frozen=True)
class Row:
    label: str | None
    visits: int


def _label(row: Row) -> str | None:
    return row.label


def test_the_first_of_a_name_stands_for_the_rest() -> None:
    rows = [Row("Toyonaka", 72), Row("Toyonaka", 11), Row("Umeda", 8), Row("Toyonaka", 9)]
    shown, held = fold_by_name(rows, _label)
    assert [row.visits for row in shown] == [72, 8]
    assert held == {0: 2}


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
