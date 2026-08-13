"""Port for keeping profiles across builds.

A protocol rather than a base class: an implementer writes a matching
class and never imports this module. See ADR-0004.
"""

from __future__ import annotations

from typing import Protocol

from kiseki.domain.interests import Profile


class ProfileRepository(Protocol):
    """Stores profiles and recalls them in the order they were saved."""

    def save(self, profile: Profile) -> None:
        """Keep a profile. The order of saving is the order of history."""
        ...

    def latest(self) -> Profile | None:
        """The most recently saved profile, or None before any save."""
        ...

    def history(self) -> tuple[Profile, ...]:
        """Every saved profile, oldest first."""
        ...
