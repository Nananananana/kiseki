"""In-memory profile repository, for tests and examples.

Runs against the same contract suite as any real implementation, so it
cannot drift from the behaviour the application relies on.
"""

from __future__ import annotations

from kiseki.domain.interests import Profile


class FakeProfileRepository:
    """Keeps profiles in memory; conforms to ProfileRepository."""

    def __init__(self) -> None:
        self._profiles: list[Profile] = []

    def save(self, profile: Profile) -> None:
        self._profiles.append(profile)

    def latest(self) -> Profile | None:
        if not self._profiles:
            return None
        return self._profiles[-1]

    def history(self) -> tuple[Profile, ...]:
        return tuple(self._profiles)
