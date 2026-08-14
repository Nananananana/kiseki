"""In-memory theme set repository, for tests and examples."""

from __future__ import annotations

from kiseki.domain.caption.themes import ThemeSet, ThemeSetKey


class FakeThemeSetRepository:
    """Keeps theme sets in memory; conforms to ThemeSetRepository."""

    def __init__(self) -> None:
        self._by_key: dict[str, ThemeSet] = {}
        self._order: list[str] = []

    def save(self, theme_set: ThemeSet) -> None:
        if theme_set.key.value not in self._by_key:
            self._order.append(theme_set.key.value)
        self._by_key[theme_set.key.value] = theme_set

    def get(self, key: ThemeSetKey) -> ThemeSet | None:
        return self._by_key.get(key.value)

    def latest(self) -> ThemeSet | None:
        if not self._order:
            return None
        return self._by_key[self._order[-1]]
