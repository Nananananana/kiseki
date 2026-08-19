"""An answer says which kinds of witness it read."""

from kiseki.application.sourcing import read_from, source_of, sources_of
from kiseki.domain.evidence.source import EvidenceSource


def test_each_prefix_names_its_kind() -> None:
    assert source_of("caption:abc") is EvidenceSource.STAY_CAPTION
    assert source_of("photo:abc") is EvidenceSource.SINGLE_CAPTION
    assert source_of("screen:abc") is EvidenceSource.SCREEN
    assert source_of("place:34.78,135.46") is EvidenceSource.JOURNEY


def test_the_index_vocabulary_maps_the_same_way() -> None:
    """Retrieval speaks stay: and single: where the profile says caption:."""
    assert source_of("stay:abc") is EvidenceSource.STAY_CAPTION
    assert source_of("single:abc") is EvidenceSource.SINGLE_CAPTION


def test_anything_else_came_from_a_photograph() -> None:
    assert source_of("ramen") is EvidenceSource.PHOTOGRAPH


def test_a_set_of_references_names_every_kind() -> None:
    found = sources_of(["caption:a", "screen:b", "caption:c"])
    assert found == {EvidenceSource.STAY_CAPTION, EvidenceSource.SCREEN}


def test_the_line_reads_like_a_sentence() -> None:
    said = read_from(["place:1,1", "caption:a", "screen:b"])
    assert said == "read from journey, stay caption and screen reading"


def test_nothing_read_says_nothing() -> None:
    assert read_from([]) == ""
