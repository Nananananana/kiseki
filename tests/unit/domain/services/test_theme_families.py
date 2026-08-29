"""A listing says each subject once, and says how much it stands for."""

from kiseki.domain.caption.themes import Theme
from kiseki.domain.services.theme_families import (
    families,
    family_of,
    fold_by_family,
)

# eating > dining > table, and nature > plant > tree, as the real set has them.
THEMES = (
    Theme(name="eating", members=("dining", "food", "restaurant")),
    Theme(name="dining", members=("table", "tableware")),
    Theme(name="nature", members=("plant", "garden")),
    Theme(name="plant", members=("tree", "forest")),
)


def test_a_topic_finds_the_top_of_its_chain() -> None:
    mapping = {"table": "dining", "dining": "eating"}
    assert family_of("table", mapping) == "eating"
    assert family_of("dining", mapping) == "eating"
    assert family_of("eating", mapping) == "eating"


def test_a_topic_in_no_family_is_its_own() -> None:
    assert family_of("ramen", {}) == "ramen"


def test_a_loop_stops_rather_than_hangs() -> None:
    mapping = {"a": "b", "b": "a"}
    assert family_of("a", mapping) in {"a", "b"}


def test_every_member_knows_its_head() -> None:
    heads = families(THEMES)
    assert heads["table"] == "eating"
    assert heads["tree"] == "nature"
    assert heads["food"] == "eating"


def test_a_listing_keeps_the_strongest_of_a_family() -> None:
    ranked = ["eating", "dining", "table", "ramen", "nature", "tree"]
    shown, held = fold_by_family(ranked, THEMES)
    assert shown == ["eating", "ramen", "nature"]
    assert held["eating"] == 2
    assert held["nature"] == 1


def test_the_specific_word_survives_when_it_leads() -> None:
    """Ranked first, the specific reading is the one shown."""
    ranked = ["table", "eating", "ramen"]
    shown, _held = fold_by_family(ranked, THEMES)
    assert shown == ["table", "ramen"]


def test_without_themes_nothing_is_folded() -> None:
    ranked = ["eating", "dining", "table"]
    shown, held = fold_by_family(ranked, ())
    assert shown == ranked
    assert held == {}
