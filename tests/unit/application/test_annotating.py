"""The boundary an outside provider speaks across."""

import pytest
from kiseki.adapters.fake.providers import FakeAnnotator
from kiseki.application.annotating import annotate_suggestions
from kiseki.domain.services.suggesting import Suggestion, SuggestionKind
from kiseki.ports.providers import MAX_NOTE_LENGTH, ProviderNote


def _suggestion(reference: str) -> Suggestion:
    return Suggestion(
        kind=SuggestionKind.DAY_TRIP,
        reference=reference,
        confidence=0.5,
        days_since=300,
        distance_km=20.0,
    )


def test_no_provider_means_no_notes() -> None:
    assert annotate_suggestions([_suggestion("place:1.0,1.0")]) == {}


def test_a_note_is_attached_to_the_suggestion_it_names() -> None:
    suggestions = [_suggestion("place:1.0,1.0")]
    notes = annotate_suggestions(suggestions, FakeAnnotator())
    assert notes["place:1.0,1.0"].note == "clear on Saturday"
    assert notes["place:1.0,1.0"].source == "fake-provider"


def test_a_note_about_somewhere_never_offered_is_dropped() -> None:
    notes = annotate_suggestions(
        [_suggestion("place:1.0,1.0")], FakeAnnotator(invent="place:9.0,9.0")
    )
    assert list(notes) == ["place:1.0,1.0"]


def test_a_provider_cannot_claim_to_be_another() -> None:
    notes = annotate_suggestions(
        [_suggestion("place:1.0,1.0")], FakeAnnotator(impersonate="weather-service")
    )
    assert notes == {}


def test_a_failing_provider_costs_the_owner_nothing() -> None:
    notes = annotate_suggestions([_suggestion("place:1.0,1.0")], FakeAnnotator(fail=True))
    assert notes == {}


def test_the_provider_sees_the_suggestions_and_returns_nothing_else() -> None:
    annotator = FakeAnnotator()
    suggestions = [_suggestion("place:1.0,1.0"), _suggestion("place:2.0,2.0")]
    annotate_suggestions(suggestions, annotator)
    assert annotator.seen == [("place:1.0,1.0", "place:2.0,2.0")]


def test_a_note_must_say_who_said_it() -> None:
    with pytest.raises(ValueError):
        ProviderNote(reference="place:1.0,1.0", source="  ", note="clear")


def test_a_note_annotates_rather_than_narrates() -> None:
    with pytest.raises(ValueError):
        ProviderNote(
            reference="place:1.0,1.0",
            source="fake",
            note="x" * (MAX_NOTE_LENGTH + 1),
        )
