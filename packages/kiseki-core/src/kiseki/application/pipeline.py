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
from kiseki.domain.services.screen_interest_derivation import (
    derive_screen_interests,
    merge_screen_interests,
)
from kiseki.domain.services.stop_extraction import extract_stops
from kiseki.domain.services.subject_interest_derivation import derive_subject_interests
from kiseki.domain.services.trend_derivation import derive_trend
from kiseki.domain.shared.geo import Distance
from kiseki.domain.shared.settings import AnchorSettings, OutingSettings, StopSettings
from kiseki.domain.trends import TrendReport
from kiseki.ports.captions import CaptionRepository
from kiseki.ports.profiles import ProfileRepository
from kiseki.ports.repositories import (
    AnchorRepository,
    OutingRepository,
    PhotoRepository,
)
from kiseki.ports.screens import ScreenshotReadingRepository
from kiseki.ports.subjects import SubjectRepository
from kiseki.ports.themes import ThemeSetRepository

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
        captions: CaptionRepository | None = None,
        subjects: SubjectRepository | None = None,
        themes: ThemeSetRepository | None = None,
        screens: ScreenshotReadingRepository | None = None,
    ) -> None:
        self._photos = photos
        self._outings = outings
        self._anchors = anchors
        self._settings = settings if settings is not None else PipelineSettings()
        self._profiles = profiles
        self._captions = captions
        self._subjects = subjects
        self._themes = themes
        self._screens = screens

    def ingest(self, observations: Sequence[PhotoObservation]) -> int:
        """Take photographs in. Safe to run over an overlapping export."""
        return self._photos.save_all(observations)

    def rebuild(self, since: datetime | None = None, until: datetime | None = None) -> BuildResult:
        """Recompute stops, outings and anchors from the stored photographs.

        Derived data is replaced wholesale rather than amended; see
        ADR-0013. Non-photograph records never shape stops or
        anchors; see ADR-0028.
        """
        observations = self._select(since, until)
        journeys = tuple(item for item in observations if item.joins_journeys)
        extraction = extract_stops(journeys, self._settings.stops)
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

    def profile(self, generated_at: datetime | None = None, keep: bool = True) -> Profile:
        """Read the built measures as interests, and keep the reading.

        Reads storage like report(); does not recompute and calls no
        model. When a profile repository was given, every reading is
        saved, so the history a trend will one day be computed from
        keeps accumulating. Pass keep=False to take a reading
        without keeping it: a served GET must change nothing.
        """
        outings = self._outings.all()
        places = summarise_places(outings, self._settings.place_radius)
        when = generated_at or datetime.now()
        profile = derive_interests(places, when, anchors=self._anchors.all())

        if self._captions is not None and self._subjects is not None:
            latest = self._themes.latest() if self._themes is not None else None
            profile = Profile(
                generated_at=when,
                interests=profile.interests
                + derive_subject_interests(
                    self._subjects.all(),
                    self._captions.all(),
                    self._photos.all(),
                    themes=latest.themes if latest is not None else (),
                ),
            )

        if self._screens is not None:
            profile = merge_screen_interests(
                profile,
                derive_screen_interests(self._screens.all(), at=profile.generated_at),
            )
        if self._profiles is not None and keep:
            self._profiles.save(profile)
        return profile

    def trend(self) -> TrendReport | None:
        """Read the drift between the kept readings.

        Compares the latest saved profile against the most recent one
        old enough to compare with, through the current theme set.
        Reads storage only; recomputes nothing and calls no model.
        None while the history is too short is itself the answer.
        See ADR-0025.
        """
        if self._profiles is None:
            return None
        latest = self._themes.latest() if self._themes is not None else None
        return derive_trend(
            self._profiles.history(),
            themes=latest.themes if latest is not None else (),
        )

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
