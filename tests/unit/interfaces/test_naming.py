"""Place topics resolve to names at display time, or stay as they are."""

from kiseki.adapters.fake.places import FakeGazetteer
from kiseki.domain.shared.geo import GeoPoint
from kiseki.interfaces.naming import place_names
from kiseki.ports.places import PlaceName

PLACE = "place:35.01160,135.76810"


def _gazetteer() -> FakeGazetteer:
    return FakeGazetteer([(GeoPoint(35.0116, 135.7681), PlaceName("Kyoto", "JP"))])


def test_a_place_topic_resolves_to_its_label():
    assert place_names([PLACE], _gazetteer()) == {PLACE: "Kyoto (JP)"}


def test_other_topics_are_left_alone():
    assert place_names(["ramen", "dining"], _gazetteer()) == {}


def test_a_malformed_place_is_skipped():
    assert place_names(["place:oops", "place:1,2,3"], _gazetteer()) == {}


def test_nothing_close_enough_stays_unnamed():
    assert place_names(["place:43.06000,141.35000"], _gazetteer()) == {}


def test_duplicates_resolve_once():
    names = place_names([PLACE, PLACE], _gazetteer())
    assert names == {PLACE: "Kyoto (JP)"}
