"""Use cases: the order in which the domain services are applied.

Everything here works through ports, so the whole sequence can be exercised
against fakes in milliseconds. That property is why the ports exist.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime

from kiseki.application.captioning import DEFAULT_IMAGES_PER_STOP, representative_photo_ids
from kiseki.application.estimating import UNKNOWN, Stage
from kiseki.application.limits import (
    ACTIVITY,
    NOTES,
    PAGES,
    PHOTOGRAPHS,
    SCREENS,
    LimitsReport,
    Source,
    Span,
    limits_of,
)
from kiseki.domain.analytics.analytics import (
    OutingHabits,
    PlacePreference,
    Rhythm,
    summarise_habits,
    summarise_places,
    summarise_rhythm,
)
from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.caption.caption import CaptionKey
from kiseki.domain.comparison import Comparison
from kiseki.domain.correction import active_exclusions
from kiseki.domain.discovery import DiscoveryFeed
from kiseki.domain.insight import InsightReport
from kiseki.domain.interests import Profile
from kiseki.domain.lifecycle import LifecycleReport
from kiseki.domain.note.reading import SENSITIVE_CATEGORIES as NOTE_SENSITIVE
from kiseki.domain.outing.outing import Outing
from kiseki.domain.photo.observation import PhotoObservation
from kiseki.domain.screen.reading import SENSITIVE_CATEGORIES as SCREEN_SENSITIVE
from kiseki.domain.services.anchor_estimation import estimate_anchors
from kiseki.domain.services.comparing import compare_profiles
from kiseki.domain.services.correcting import apply_corrections
from kiseki.domain.services.detectors import DEFAULT_DETECTOR, StopDetector
from kiseki.domain.services.discovering import derive_discoveries
from kiseki.domain.services.insight_derivation import derive_insights
from kiseki.domain.services.interest_derivation import derive_interests
from kiseki.domain.services.lifecycle_derivation import derive_lifecycles
from kiseki.domain.services.note_interest_derivation import (
    derive_note_interests,
    merge_note_interests,
)
from kiseki.domain.services.outing_assembly import assemble_outings
from kiseki.domain.services.screen_interest_derivation import (
    derive_screen_interests,
    merge_screen_interests,
)
from kiseki.domain.services.stop_extraction import extract_stops
from kiseki.domain.services.subject_interest_derivation import derive_subject_interests
from kiseki.domain.services.trend_derivation import MIN_TREND_SPAN_DAYS, derive_trend
from kiseki.domain.services.vocabulary import overlap_of
from kiseki.domain.shared.geo import Distance
from kiseki.domain.shared.moment import naive
from kiseki.domain.shared.settings import AnchorSettings, OutingSettings, StopSettings
from kiseki.domain.trends import TrendReport
from kiseki.domain.web.reading import UNLABELLED_CATEGORIES as PAGE_UNLABELLED
from kiseki.ports.activity import DailyActivityRepository
from kiseki.ports.captions import CaptionRepository
from kiseki.ports.corrections import CorrectionRepository
from kiseki.ports.notes import NoteReadingRepository
from kiseki.ports.profiles import ProfileRepository
from kiseki.ports.repositories import (
    AnchorRepository,
    OutingRepository,
    PhotoRepository,
)
from kiseki.ports.screens import ScreenshotReadingRepository
from kiseki.ports.singles import SingleCaptionRepository
from kiseki.ports.subjects import SubjectRepository
from kiseki.ports.themes import ThemeSetRepository
from kiseki.ports.web import PageReadingRepository

DEFAULT_PLACE_RADIUS = Distance(500)


@dataclass(frozen=True)
class PipelineSettings:
    stops: StopSettings = field(default_factory=StopSettings)
    outings: OutingSettings = field(default_factory=OutingSettings)
    anchors: AnchorSettings = field(default_factory=AnchorSettings)
    place_radius: Distance = DEFAULT_PLACE_RADIUS
    stop_detector: StopDetector | None = None
    """Which algorithm separates stays from journeys, already resolved.

    A callable and not a name, because **resolving a name is not this
    layer's to do**: the accelerated detectors live in the adapters
    layer, which sits above this one, and an application that reached
    up to it would invert the dependency the architecture check keeps
    (`lint-imports` refused exactly that when this was written the
    other way). The interface resolves the name and hands down what it
    resolved. `None` means the domain default.
    """

    stop_detector_name: str = DEFAULT_DETECTOR
    """The same choice as a word, kept for reporting.

    A callable cannot go in a build report or a bug report, and two
    libraries built with different detectors are not comparable
    however alike their numbers look -- so the name travels beside the
    thing it named."""


@dataclass(frozen=True)
class BuildResult:
    """What a rebuild produced, for reporting back to whoever asked."""

    photographs: int
    stops: int
    outings: int
    anchors: int
    in_transit: int
    unlocated: int
    detector: str = DEFAULT_DETECTOR
    """Which algorithm produced these stops. Printed by `kiseki build`
    because a derivation that cannot say what made it is a derivation
    nobody can argue with -- and because two libraries built with
    different detectors are not comparable, however alike the numbers
    look."""


@dataclass(frozen=True)
class Report:
    """Everything measured, ready to be rendered or serialised."""

    photographs: int
    anchors: tuple[Anchor, ...]
    outings: tuple[Outing, ...]
    places: PlacePreference
    habits: OutingHabits | None
    rhythm: Rhythm


@dataclass(frozen=True)
class PrivacyReport:
    """How the library treats the owner's data, in counts (ADR-0046)."""

    photographs: int
    located: int
    withheld_from_preference: int
    stay_captions: int
    stay_refused: int
    single_captions: int
    single_refused: int
    screen_readings: int
    screens_label_silent: int
    subject_readings: int
    note_readings: int
    notes_label_silent: int
    activity_days: int
    page_readings: int
    pages_label_silent: int
    kept_profiles: int
    corrections: int
    active_exclusions: int


def _naive(moment: datetime) -> datetime:
    return naive(moment)


def _latest_at_or_before(history: Sequence[Profile], moment: datetime) -> Profile | None:
    chosen: Profile | None = None
    for profile in history:
        if _naive(profile.generated_at) <= _naive(moment):
            chosen = profile
    return chosen


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
        notes: NoteReadingRepository | None = None,
        activity: DailyActivityRepository | None = None,
        pages: PageReadingRepository | None = None,
        singles: SingleCaptionRepository | None = None,
        corrections: CorrectionRepository | None = None,
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
        self._notes = notes
        self._activity = activity
        self._pages = pages
        self._singles = singles
        self._corrections = corrections

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
        extraction = extract_stops(
            journeys, self._settings.stops, detector=self._settings.stop_detector
        )
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
            detector=self._settings.stop_detector_name,
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
                    singles=self._singles.all() if self._singles is not None else (),
                ),
            )

        if self._screens is not None:
            profile = merge_screen_interests(
                profile,
                derive_screen_interests(self._screens.all(), at=profile.generated_at),
            )
        if self._notes is not None:
            # Last, and append-only: a photograph of a thing is stronger
            # evidence of caring about it than a word in a file
            # (ADR-0080).
            profile = merge_note_interests(profile, derive_note_interests(self._notes.all()))
        if self._profiles is not None and keep:
            self._profiles.save(profile)
        return self._corrected(profile)

    def _corrected(self, profile: Profile) -> Profile:
        """The reading through the correction log. Stored bytes untouched."""
        if self._corrections is None:
            return profile
        return apply_corrections(profile, active_exclusions(self._corrections.all()))

    def _kept_history(self) -> tuple[Profile, ...]:
        history = self._profiles.history() if self._profiles is not None else ()
        return tuple(self._corrected(profile) for profile in history)

    def outstanding_model_work(self) -> tuple[Stage, ...]:
        """How many items each model stage still has to look at.

        Counted from storage rather than estimated: every stage here
        already knows how to skip what is done, and this asks the same
        question without doing the work.

        A stage whose repository is absent is `UNKNOWN` and not zero.
        A library with no caption repository has not finished
        captioning; it cannot caption at all, and reporting nothing
        left to do would be a confident lie.
        """
        photos = self._photos.all()
        outings = self._outings.all()

        if self._captions is None:
            stays = UNKNOWN
        else:
            referenced = {
                item.photo_id
                for item in photos
                if item.thumbnail_ref and item.may_inform_preferences
            }
            stays = 0
            for outing in outings:
                for stop in outing.stops:
                    eligible = [one for one in stop.photo_ids if one in referenced]
                    if not eligible:
                        continue
                    selected = representative_photo_ids(eligible, DEFAULT_IMAGES_PER_STOP)
                    if self._captions.get(CaptionKey.of(selected)) is None:
                        stays += 1

        in_a_stop = {
            photo for outing in outings for stop in outing.stops for photo in stop.photo_ids
        }
        if self._singles is None:
            singles = UNKNOWN
        else:
            singles = sum(
                1
                for item in photos
                if item.photo_id not in in_a_stop
                and item.thumbnail_ref
                and item.may_inform_preferences
                and item.content_kind == "photo"
                and self._singles.get(item.photo_id) is None
            )

        if self._screens is None:
            screens = UNKNOWN
        else:
            screens = sum(
                1
                for item in photos
                if item.content_kind == "screenshot"
                and item.thumbnail_ref
                and self._screens.get(item.photo_id) is None
            )

        if self._subjects is None or self._captions is None:
            subjects = UNKNOWN
        else:
            subjects = sum(
                1 for caption in self._captions.all() if self._subjects.get(caption.key) is None
            )

        return (
            Stage("stay captions", stays, None, "a stay, described from its photographs"),
            Stage("single captions", singles, None, "a photograph outside every stay"),
            Stage("screen readings", screens, None, "a screenshot, as category and labels"),
            Stage("subject readings", subjects, None, "a caption, read for its subjects"),
        )

    def privacy(self) -> PrivacyReport:
        """How the owner's data is treated, counted from storage.

        Reads storage only; recomputes nothing and calls no model.
        Repositories that were never wired count as zero, honestly.
        """
        photos = self._photos.all()
        captions = self._captions.all() if self._captions is not None else ()
        singles = self._singles.all() if self._singles is not None else ()
        screens = self._screens.all() if self._screens is not None else ()
        subjects = self._subjects.all() if self._subjects is not None else ()
        notes = self._notes.all() if self._notes is not None else ()
        days = self._activity.all() if self._activity is not None else ()
        pages = self._pages.all() if self._pages is not None else ()
        history = self._profiles.history() if self._profiles is not None else ()
        corrections = self._corrections.all() if self._corrections is not None else ()
        return PrivacyReport(
            photographs=len(photos),
            located=sum(1 for photo in photos if photo.is_located),
            withheld_from_preference=sum(
                1 for photo in photos if photo.use_for_preference is False
            ),
            stay_captions=len(captions),
            stay_refused=sum(1 for caption in captions if caption.refused is not None),
            single_captions=len(singles),
            single_refused=sum(1 for single in singles if single.refused is not None),
            screen_readings=len(screens),
            screens_label_silent=sum(
                1 for reading in screens if reading.refused is None and not reading.labels
            ),
            subject_readings=len(subjects),
            note_readings=len(notes),
            notes_label_silent=sum(
                1 for reading in notes if reading.refused is None and not reading.labels
            ),
            activity_days=len(days),
            page_readings=len(pages),
            pages_label_silent=sum(
                1 for reading in pages if reading.refused is None and not reading.labels
            ),
            kept_profiles=len(history),
            corrections=len(corrections),
            active_exclusions=len(active_exclusions(corrections)),
        )

    def limits(self) -> LimitsReport:
        """What this installation cannot answer, from its own counts.

        Reads storage only; recomputes nothing and calls no model, as
        `privacy` does. The vocabulary limit is derived from the same
        `compare` this library prints, so the two can never disagree.
        """

        def span_of(days: Sequence[date]) -> Span | None:
            return Span(first=min(days), last=max(days)) if days else None

        photos = self._photos.all()
        taken = {photo.photo_id: photo.captured_at for photo in photos}
        """A screen reading is dated by the screenshot, never by itself.

        `ScreenshotReading.created_at` is when the model read it, so a
        captioning run that took four days made 297 readings look like
        four days of evidence. Measured on the real library: the
        readings sat inside 2026-08-15..19 while the screenshots they
        describe span 2024-07-10..2026-08-09 -- 5 days reported
        against 761 actual."""
        notes = self._notes.all() if self._notes is not None else ()
        pages = self._pages.all() if self._pages is not None else ()
        activity = self._activity.all() if self._activity is not None else ()
        screens = self._screens.all() if self._screens is not None else ()

        sources = (
            Source(
                name=PHOTOGRAPHS,
                count=len(photos),
                span=span_of([photo.captured_at.date() for photo in photos]),
            ),
            Source(
                name=NOTES,
                count=len(notes),
                span=span_of([reading.day for reading in notes]),
            ),
            Source(
                name=PAGES,
                count=len(pages),
                span=span_of([reading.day for reading in pages]),
            ),
            Source(
                name=ACTIVITY,
                count=len(activity),
                span=span_of([day.day for day in activity]),
            ),
            Source(
                name=SCREENS,
                count=len(screens),
                span=span_of(
                    [
                        taken[reading.photo_id].date()
                        for reading in screens
                        if reading.photo_id in taken
                    ]
                ),
            ),
        )

        captions = self._captions.all() if self._captions is not None else ()
        singles = self._singles.all() if self._singles is not None else ()
        refusals = sum(1 for one in captions if one.refused is not None)
        refusals += sum(1 for one in singles if one.refused is not None)
        withheld = 0
        label_silent = 0
        for readings, never_labelled in (
            (screens, SCREEN_SENSITIVE),
            (notes, NOTE_SENSITIVE),
            (pages, PAGE_UNLABELLED),
        ):
            for one in readings:
                if one.refused is not None or one.labels:
                    continue
                if one.category in never_labelled:
                    withheld += 1
                else:
                    label_silent += 1

        comparison = self.compare()
        overlap = (
            overlap_of(
                (entry.strength_before, entry.strength_after) for entry in comparison.entries
            )
            if comparison is not None
            else None
        )

        return limits_of(
            sources,
            overlap=overlap,
            refusals=refusals,
            label_silent=label_silent,
            withheld=withheld,
        )

    def compare(
        self,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
    ) -> Comparison | None:
        """What changed between two kept readings (ADR-0045).

        Defaults to the trend's pair: the latest reading against the
        most recent one old enough to compare with. With both dates,
        picks the latest kept reading at or before each. None while
        the history cannot supply a pair.
        """
        history = self._kept_history()
        if not history:
            return None
        latest = self._themes.latest() if self._themes is not None else None
        themes = latest.themes if latest is not None else ()
        if from_at is not None and to_at is not None:
            before = _latest_at_or_before(history, from_at)
            after = _latest_at_or_before(history, to_at)
        else:
            after = history[-1]
            before = None
            for profile in history[:-1]:
                gap = _naive(after.generated_at) - _naive(profile.generated_at)
                if gap.days >= MIN_TREND_SPAN_DAYS:
                    before = profile
        if before is None or after is None:
            return None
        return compare_profiles(before, after, themes=themes)

    def discover(self) -> DiscoveryFeed | None:
        """What is worth a look, from the kept readings (ADR-0048)."""
        if self._profiles is None:
            return None
        latest = self._themes.latest() if self._themes is not None else None
        return derive_discoveries(
            self._profiles.history(),
            themes=latest.themes if latest is not None else (),
        )

    def insights(self) -> InsightReport | None:
        """The current findings, from the kept readings."""
        if self._profiles is None:
            return None
        latest = self._themes.latest() if self._themes is not None else None
        return derive_insights(
            self._kept_history(),
            themes=latest.themes if latest is not None else (),
        )

    def lifecycle(self) -> LifecycleReport | None:
        """Where each topic stands in its life, from the kept readings."""
        if self._profiles is None:
            return None
        latest = self._themes.latest() if self._themes is not None else None
        return derive_lifecycles(
            self._kept_history(),
            themes=latest.themes if latest is not None else (),
        )

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
            self._kept_history(),
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
