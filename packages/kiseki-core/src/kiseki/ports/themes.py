"""Port for keeping theme sets.

Keyed by the label universe; the store doubles as the progress record
(ADR-0023), like captions and subject readings before it.
"""

from typing import Protocol

from kiseki.domain.caption.themes import ThemeSet, ThemeSetKey


class ThemeSetRepository(Protocol):
    """Stores theme sets by key and recalls the most recent one."""

    def save(self, theme_set: ThemeSet) -> None:
        """Keep a set, replacing any existing one with the same key."""
        ...

    def get(self, key: ThemeSetKey) -> ThemeSet | None:
        """The set for this label universe, or None if not yet made."""
        ...

    def latest(self) -> ThemeSet | None:
        """The most recently saved set, or None before any save."""
        ...
