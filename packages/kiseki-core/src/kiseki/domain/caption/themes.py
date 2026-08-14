"""Themes: labels gathered under a name.

A theme set is keyed by the whole label universe it was computed from,
so the store doubles as the progress record: as long as the labels
have not changed, the themes stand; when a new label appears, the key
changes and the set is computed anew. See ADR-0023.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

KEY_LENGTH = 16


@dataclass(frozen=True)
class ThemeSetKey:
    """Derived from the label universe, so it changes when the labels do."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("a theme set key cannot be empty")

    @classmethod
    def of(cls, labels: Sequence[str]) -> "ThemeSetKey":
        if not labels:
            raise ValueError("a theme set key needs at least one label")
        joined = "|".join(sorted(labels))
        return cls(hashlib.sha256(joined.encode("utf-8")).hexdigest()[:KEY_LENGTH])


@dataclass(frozen=True)
class Theme:
    """Labels that belong together, under a name.

    A single label is not a theme -- it is just the label, and it
    keeps speaking for itself in the profile.
    """

    name: str
    members: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a theme needs a name")
        if len(self.members) < 2:
            raise ValueError("a theme needs at least two members")
        if any(not member.strip() for member in self.members):
            raise ValueError("a member label cannot be blank")


@dataclass(frozen=True)
class ThemeSet:
    """Every theme read from one label universe. May be empty."""

    key: ThemeSetKey
    themes: tuple[Theme, ...]
    model: str
    created_at: datetime
