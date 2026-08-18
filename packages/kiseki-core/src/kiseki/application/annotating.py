"""Attaches outside notes to suggestions, without letting them in.

Everything a provider returns passes through here, and this is where
the boundary is enforced rather than assumed: a note about something
the owner was never offered is dropped, a note from a provider that
names itself differently than it claims is dropped, and the
suggestions themselves come back in the order and number they went in.

A provider that fails does not fail the suggestion: an unavailable
annotator leaves the notes empty, exactly as an unavailable embedder
leaves retrieval on the words channel (ADR-0037). See ADR-0056.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from kiseki.domain.services.suggesting import Suggestion
from kiseki.ports.providers import ProviderNote, SuggestionAnnotator

NOTES_PER_SUGGESTION = 1


def annotate_suggestions(
    suggestions: Sequence[Suggestion],
    annotator: SuggestionAnnotator | None = None,
) -> Mapping[str, ProviderNote]:
    """The notes worth showing, one per suggestion, keyed by reference.

    Never raises on a provider's account: whatever goes wrong outside
    the library, the owner still gets their suggestions.
    """
    if annotator is None or not suggestions:
        return {}
    offered = {suggestion.reference for suggestion in suggestions}
    try:
        returned = list(annotator.annotate(suggestions))
        source = annotator.source
    except Exception:
        return {}
    notes: dict[str, ProviderNote] = {}
    for note in returned:
        if note.reference not in offered:
            continue
        if note.source != source:
            continue
        if note.reference in notes:
            continue
        notes[note.reference] = note
    return notes
