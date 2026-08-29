"""A theme set is read the same way wherever it is read."""

from kiseki.domain.caption.themes import Theme
from kiseki.domain.services.theme_mapping import merged_themes, theme_mapping


def test_members_map_to_their_theme() -> None:
    themes = (Theme(name="eating", members=("ramen", "udon")),)
    assert theme_mapping(themes) == {"ramen": "eating", "udon": "eating"}


def test_a_generic_theme_name_maps_nothing() -> None:
    """The naming model called one cluster "text"; it is not a topic."""
    themes = (
        Theme(name="text", members=("text", "document")),
        Theme(name="eating", members=("ramen", "udon")),
    )
    assert theme_mapping(themes) == {"ramen": "eating", "udon": "eating"}


def test_two_themes_of_one_name_are_one_theme() -> None:
    themes = (
        Theme(name="transport", members=("road", "street")),
        Theme(name="transport", members=("car", "road")),
    )
    mapping = theme_mapping(themes)
    assert mapping == {"road": "transport", "street": "transport", "car": "transport"}


def test_merging_keeps_every_member_once() -> None:
    themes = (
        Theme(name="transport", members=("road", "street")),
        Theme(name="transport", members=("car", "road")),
        Theme(name="object", members=("object", "digital object")),
    )
    merged = merged_themes(themes)
    assert len(merged) == 1
    assert merged[0].name == "transport"
    assert merged[0].members == ("road", "street", "car")


def test_a_member_of_two_themes_keeps_the_first() -> None:
    themes = (
        Theme(name="eating", members=("rice", "bowl")),
        Theme(name="cooking", members=("rice", "pan")),
    )
    assert theme_mapping(themes)["rice"] == "eating"


def test_nothing_in_is_nothing_out() -> None:
    assert theme_mapping(()) == {}
    assert merged_themes(()) == ()
