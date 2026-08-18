"""A narration that reads well can still say what no fact says."""

from kiseki.application.narration_validation import (
    NarrationDefect,
    cited_facts,
    validate_narration,
)

FACTS = (
    "4956 photographs and 204 outings were measured.",
    "161 distinct places were visited; 82% were never returned to.",
    "37% of outings happened on weekends.",
)


def test_a_supported_narration_has_no_defects() -> None:
    story = "You measured 4956 photographs across 204 outings [F1]."
    assert validate_narration(story, FACTS) == ()


def test_a_narration_without_a_citation_is_a_defect() -> None:
    story = "You measured 4956 photographs across 204 outings."
    assert validate_narration(story, FACTS) == (NarrationDefect.UNCITED,)


def test_a_citation_beyond_the_facts_is_a_defect() -> None:
    story = "You visited 161 places [F9]."
    assert NarrationDefect.UNKNOWN_CITATION in validate_narration(story, FACTS)


def test_a_range_is_read_as_the_facts_it_names() -> None:
    assert cited_facts("subjects recorded over time [F1-F3]") == (1, 2, 3)
    assert validate_narration("161 places, 82% never again [F1-F3]", FACTS) == ()


def test_a_range_beyond_the_facts_is_still_a_defect() -> None:
    story = "your subjects [F1-F16]"
    assert NarrationDefect.UNKNOWN_CITATION in validate_narration(story, FACTS)


def test_a_number_no_fact_states_is_a_defect() -> None:
    """The facts said 82 per cent were never returned to."""
    story = "Only 18% of your places were revisited [F2]."
    assert NarrationDefect.UNSUPPORTED_NUMBER in validate_narration(story, FACTS)


def test_a_number_the_facts_contain_is_fine() -> None:
    story = "37% of your outings were at weekends, across 204 of them [F1][F3]."
    assert validate_narration(story, FACTS) == ()


def test_an_empty_narration_is_left_alone() -> None:
    assert validate_narration("", FACTS) == ()
    assert validate_narration("anything [F1]", ()) == ()
