"""Use cases: the order in which the domain services are applied.

Everything here works through ports, so the whole sequence can be exercised
against fakes in milliseconds. That property is why the ports exist.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from kiseki.domain.analytics.analytics import (
    OutingHabits,
    PlacePreference,
    Rhythm,
    summarise_habits,
    summarise_places,
    summarise_rhythm,
)
from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.interests import Profile
from kiseki.domain.outing.outing import Outing
from kiseki.domain.photo.observation import PhotoObservation
from kiseki.domain.services.anchor_estimation import estimate_anchors
from kiseki.domain.services.interest_derivation import derive_interests
from kiseki.domain.services.outing_assembly import assemble_outings
from kiseki.domain.services.stop_extraction import extract_stops
from kiseki.domain.shared.geo import Distance
from kiseki.domain.shared.settings import AnchorSettings, OutingSettings, StopSettings
from kiseki.ports.profiles import ProfileRepository
from kiseki.ports.repositories import (
    AnchorRepository,
    OutingRepository,
    PhotoRepository,
)

DEFAULT_PLACE_RADIUS = Distance(500)


@dataclass(frozen=True)
class PipelineSettings:
    stops: StopSettings = field(default_factory=StopSettings)
    outings: OutingSettings = field(default_factory=OutingSettings)
    anchors: AnchorSettings = field(default_factory=AnchorSettings)
    place_radius: Distance = DEFAULT_PLACE_RADIUS


@dataclass(frozen=True)
class BuildResult:
    """What a rebuild produced, for reporting back to whoever asked."""

    photographs: int
    stops: int
    outings: int
    anchors: int
    in_transit: int
    unlocated: int


@dataclass(frozen=True)
class Report:
    """Everything measured, ready to be rendered or serialised."""

    photographs: int
    anchors: tuple[Anchor, ...]
    outings: tuple[Outing, ...]
    places: PlacePreference
    habits: OutingHabits | None
    rhythm: Rhythm


class Pipeline:
    def __init__(
        self,
        photos: PhotoRepository,
        outings: OutingRepository,
        anchors: AnchorRepository,
        settings: PipelineSettings | None = None,
        profiles: ProfileRepository | None = None,
    ) -> None:
        self._photos = photos
        self._outings = outings
        self._anchors = anchors
        self._settings = settings if settings is not None else PipelineSettings()
        self._profiles = profiles

    def ingest(self, observations: Sequence[PhotoObservation]) -> int:
        """Take photographs in. Safe to run over an overlapping export."""
        return self._photos.save_all(observations)

    def rebuild(self, since: datetime | None = None, until: datetime | None = None) -> BuildResult:
        """Recompute stops, outings and anchors from the stored photographs.

        Derived data is replaced wholesale rather than amended; see ADR-0013.
        """
        observations = self._select(since, until)
        extraction = extract_stops(observations, self._settings.stops)
        outings = assemble_outings(extraction.stops, self._settings.outings)
        anchors = estimate_anchors(extraction.stops, self._settings.anchors)

        self._outings.replace_all(outings)
        self._anchors.replace_all(anchors)

        return BuildResult(
            photographs=len(observations),
            stops=len(extraction.stops),
            outings=len(outings),
            anchors=len(anchors),
            in_transit=len(extraction.in_transit),
            unlocated=len(extraction.unlocated),
        )

    def report(self) -> Report:
        """Measure what has been built. Reads storage; does not recompute."""
        outings = self._outings.all()
        return Report(
            photographs=self._photos.count(),
            anchors=self._anchors.all(),
            outings=outings,
            places=summarise_places(outings, self._settings.place_radius),
            habits=summarise_habits(outings) if outings else None,
            rhythm=summarise_rhythm(outings),
        )

    def profile(self, generated_at: datetime | None = None) -> Profile:
        """Read the built measures as interests, and keep the reading.

        Reads storage like report(); does not recompute. When a profile
        repository was given, every reading is saved, so the history a
        trend will one day be computed from starts accumulating now.
        """
        outings = self._outings.all()
        places = summarise_places(outings, self._settings.place_radius)
        profile = derive_interests(
            places, generated_at or datetime.now(), anchors=self._anchors.all()
        )
        if self._profiles is not None:
            self._profiles.save(profile)
        return profile

    def _select(
        self, since: datetime | None, until: datetime | None
    ) -> tuple[PhotoObservation, ...]:
        if since is None and until is None:
            return self._photos.all()

        everything = self._photos.all()
        if not everything:
            return ()

        low = since or min(item.captured_at for item in everything)
        high = until or max(item.captured_at for item in everything)
        return self._photos.between(low, high)
