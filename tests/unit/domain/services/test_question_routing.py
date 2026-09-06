"""A question is read for the derivations that bear on it (ADR-0090).

There is no dataset of questions to derivations and none was invented:
what is held here is that the table routes as it reads, that the
questions measured on the real library before any of this route the way
that measurement said they should, and that nothing outside the table
routes at all.
"""

import pytest
from kiseki.application.grounding import KINDS as GROUNDING_KINDS
from kiseki.domain.services.question_routing import (
    COMMAND_FOR,
    INTEREST,
    KINDS,
    PHRASES,
    PLACE,
    RHYTHM,
    TREND,
    Route,
    route,
)


def test_every_kind_has_phrases_and_a_command() -> None:
    """The population, before anything is trusted about it."""
    assert set(PHRASES) == set(KINDS)
    assert set(COMMAND_FOR) == set(KINDS)
    for kind in KINDS:
        assert PHRASES[kind], kind


def test_the_kinds_are_the_grounding_kinds() -> None:
    """A route names the facts it selects. If these drift apart, a route
    selects nothing and no test would otherwise notice."""
    assert set(KINDS) <= set(GROUNDING_KINDS), sorted(set(KINDS) - set(GROUNDING_KINDS))


@pytest.mark.parametrize("kind", KINDS)
def test_every_phrase_routes_to_the_kind_it_is_listed_under(kind: str) -> None:
    """The table is the specification; this is that the code agrees with
    it. Not evidence that the vocabulary is right -- see ADR-0090."""
    for phrase in PHRASES[kind]:
        assert kind in route(phrase).kinds, f"{phrase!r} did not route to {kind}"


def test_a_retrieval_question_routes_to_nothing() -> None:
    """Measured on the real library before routing existed: this one was
    answered well by retrieval, and must keep being."""
    asked = route("what did I eat in Seoul?")
    assert not asked.routed
    assert asked.kinds == frozenset()
    assert asked.commands == ()


def test_the_question_the_grounding_docstring_measured_routes_to_place() -> None:
    asked = route("where do I keep going back to?")
    assert PLACE in asked.kinds
    assert "kiseki places" in asked.commands


def test_a_question_about_two_things_takes_both() -> None:
    """Going out is the rhythm; less than last year is the trend. Nothing
    here picks a winner, because nothing here knows enough to."""
    asked = route("am I going out less than last year?")
    assert asked.kinds == frozenset({RHYTHM, TREND})
    assert asked.commands == ("kiseki report", "kiseki trend")


def test_japanese_routes_the_same_way() -> None:
    assert route("\u5916\u51fa\u306f\u6e1b\u3063\u305f?").kinds == frozenset({RHYTHM, TREND})
    assert PLACE in route("\u3069\u3053\u306b\u3088\u304f\u884c\u304f?").kinds
    assert INTEREST in route("\u6700\u8fd1\u4f55\u306b\u30cf\u30de\u3063\u3066\u308b?").kinds


def test_an_english_phrase_does_not_fire_inside_a_word() -> None:
    """`trips` lives inside `strips` and `into` inside `intonation`.

    The first version of this test used `pointed`, which does not
    contain `into` at all -- it passed with the word-boundary check
    deleted, which is the only thing it was there to hold.
    """
    assert not route("what do the paper strips say?").routed
    assert not route("was the intonation odd?").routed
    assert RHYTHM in route("how many trips?").kinds
    assert INTEREST in route("what am I into?").kinds


def test_the_route_says_why_and_not_only_where() -> None:
    asked = route("how often do I go out?")
    assert RHYTHM in asked.kinds
    assert ("rhythm", "how often") in asked.matched


def test_a_route_cannot_name_a_kind_that_is_not_one() -> None:
    with pytest.raises(ValueError, match="not kinds"):
        Route(kinds=frozenset({"weather"}), matched=())
