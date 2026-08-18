"""A provider that invents nothing, for tests and for the conformance kit."""

from __future__ import annotations

from collections.abc import Sequence

from kiseki.domain.services.suggesting import Suggestion
from kiseki.ports.providers import ProviderNote


class FakeAnnotator:
    """Notes every suggestion it is given, or misbehaves on request.

    The misbehaviours are the ones the boundary exists to absorb: a
    note about a place nobody was offered, a note claiming another
    source, and a provider that simply fails.
    """

    def __init__(
        self,
        source: str = "fake-provider",
        note: str = "clear on Saturday",
        invent: str | None = None,
        impersonate: str | None = None,
        fail: bool = False,
    ) -> None:
        self._source = source
        self._note = note
        self._invent = invent
        self._impersonate = impersonate
        self._fail = fail
        self.seen: list[tuple[str, ...]] = []

    @property
    def source(self) -> str:
        return self._source

    def annotate(self, suggestions: Sequence[Suggestion]) -> list[ProviderNote]:
        if self._fail:
            raise RuntimeError("the provider is unavailable")
        self.seen.append(tuple(suggestion.reference for suggestion in suggestions))
        notes = [
            ProviderNote(
                reference=suggestion.reference,
                source=self._impersonate or self._source,
                note=self._note,
            )
            for suggestion in suggestions
        ]
        if self._invent is not None:
            notes.append(ProviderNote(reference=self._invent, source=self._source, note=self._note))
        return notes
