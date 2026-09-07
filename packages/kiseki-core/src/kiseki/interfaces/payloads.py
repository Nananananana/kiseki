"""JSON shapes for what the library measures and reads.

One place builds every payload, so the command line and the HTTP
server cannot drift apart. Blurring lives here because the payloads
are where coordinates become visible: served output blurs by default
(ADR-0026), while the local command line shows what is stored.
"""

from __future__ import annotations

import contextlib
import pathlib
from collections.abc import Mapping, Sequence
from datetime import datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as metadata_version
from typing import Any

from kiseki.application.asking import Answer
from kiseki.application.limits import LimitsReport
from kiseki.application.narrative import Narration
from kiseki.application.now import Now
from kiseki.application.pipeline import PrivacyReport, Report, SuggestionSet
from kiseki.application.today import Today
from kiseki.config.paths import StoragePaths
from kiseki.domain.comparison import Comparison
from kiseki.domain.discovery import DiscoveryFeed
from kiseki.domain.insight import InsightReport
from kiseki.domain.interests import Profile
from kiseki.domain.lifecycle import LifecycleReport
from kiseki.domain.services.mixing import derive_mixed
from kiseki.domain.services.place_reading import PlaceProfile
from kiseki.domain.services.suggesting import Suggestion
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.moment import naive
from kiseki.domain.trends import TrendReport
from kiseki.interfaces.claims import NEVER_STORED, UNSEEABLE
from kiseki.interfaces.failures import CATALOGUE, CONTRACT, OPEN_NAMESPACES

BLUR_DECIMALS = 2
"""Decimal places kept when blurring: roughly a kilometre grid,
enough to say "around here" without saying "this doorstep"."""

PLACE_PREFIX = "place:"


SERVED_VERSION = 1
"""Every served document carries its contract name and this version, in
the export's shape (ADR-0081). A reader that refuses unknown names can
list these; a reader that pins a version notices when one moves."""


def _installed_version() -> str:
    """The version of this library, or a word saying it is unknown.

    Running from a source tree that was never installed is normal
    during development, and a document that refused to be written
    there would be one the developer never sees.
    """
    with contextlib.suppress(PackageNotFoundError):
        return metadata_version("kiseki")
    return "unknown"


def named(endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """A served or written document, naming itself.

    `schema` first and `version` second, before the body's own keys, so
    a reader glancing at the first line knows what it is holding.
    """
    return {"schema": f"kiseki-{endpoint}", "version": SERVED_VERSION, **body}


def report_payload(report: Report, blur: bool = True) -> dict[str, Any]:
    habits = report.habits
    return named(
        "report",
        {
            "photographs": report.photographs,
            "outings": len(report.outings),
            "anchors": [
                {
                    "latitude": _blur_value(anchor.area.center.latitude, blur),
                    "longitude": _blur_value(anchor.area.center.longitude, blur),
                    "visit_days": anchor.visit_days,
                    "night_share": anchor.night_share,
                    "weekday_share": anchor.weekday_share,
                    "daytime_share": anchor.daytime_share,
                    "photograph_count": anchor.photograph_count,
                }
                for anchor in report.anchors
            ],
            "places": {
                "distinct": len(report.places.places),
                "return_rate": report.places.return_rate,
                "one_time_rate": report.places.one_time_rate,
            },
            "habits": None
            if habits is None
            else {
                "travel_km_median": habits.travel_km.median,
                "duration_hours_median": habits.duration_hours.median,
                "stops_per_outing_median": habits.stops_per_outing.median,
                "stay_minutes_median": habits.stay_minutes.median,
            },
            "rhythm": {
                "weekend_share": report.rhythm.weekend_share,
                "early_start_share": report.rhythm.early_start_share,
                "by_weekday": report.rhythm.by_weekday,
                "by_month": report.rhythm.by_month,
            },
        },
    )


def profile_payload(profile: Profile, blur: bool = True) -> dict[str, Any]:
    return named(
        "profile",
        {
            "generated_at": profile.generated_at.isoformat(),
            "interests": [
                {
                    "topic": _blur_place(interest.topic, blur),
                    "score": interest.score,
                    "confidence": interest.confidence,
                    "first_seen": interest.first_seen.isoformat(),
                    "last_seen": interest.last_seen.isoformat(),
                    "evidence": [
                        {
                            "kind": evidence.kind.value,
                            "reference": _blur_place(evidence.reference, blur),
                            "observed_at": evidence.observed_at.isoformat(),
                        }
                        for evidence in interest.evidence
                    ],
                }
                for interest in profile.ranked()
            ],
        },
    )


def trend_payload(report: TrendReport, blur: bool = True) -> dict[str, Any]:
    return named(
        "trend",
        {
            "baseline_at": report.baseline_at.isoformat(),
            "latest_at": report.latest_at.isoformat(),
            "trends": [
                {
                    "topic": _blur_place(trend.topic, blur),
                    "direction": trend.direction.value,
                    "strength": trend.strength,
                    "baseline": trend.baseline,
                }
                for trend in report.trends
            ],
        },
    )


def answer_payload(answer: Answer, blur: bool = True) -> dict[str, Any]:
    """The answer as a document, blurred unless raw is asked for.

    Blurred by default, as its siblings are, because this one accepted
    `blur` and ignored it: `/ask` over HTTP and `kiseki ask --json`
    both served `supporting_insights[].topic` raw, and an insight's
    topic can be `place:lat,lon`. Every other served payload blurs
    (ADR-0026, docs/cli.md); this one said it did and did not. A
    default of True means a caller that forgets is safe rather than
    leaking.
    """
    return named(
        "ask",
        {
            "question": answer.question,
            "answer": answer.answer if answer.answered else None,
            "confidence": answer.confidence,
            "first_seen": answer.first_seen.isoformat() if answer.first_seen else None,
            "last_seen": answer.last_seen.isoformat() if answer.last_seen else None,
            "model": answer.model,
            "since": answer.since.isoformat() if answer.since else None,
            "until": answer.until.isoformat() if answer.until else None,
            "routed_to": sorted(answer.route.kinds),
            "routed_by": [
                {"kind": kind, "phrase": phrase} for kind, phrase in answer.route.matched
            ],
            "unanswerable": list(answer.unanswerable),
            "supporting_insights": [
                {
                    "topic": _blur_place(item.topic, blur),
                    "kind": item.kind.value,
                    "magnitude": item.magnitude,
                    "confidence": item.confidence,
                }
                for item in answer.supporting_insights
            ],
            "evidence": [
                {
                    "doc_key": item.document.doc_key,
                    "kind": item.document.kind,
                    "observed_at": item.document.observed_at.isoformat(),
                    "text": item.document.text,
                    "score": item.score,
                }
                for item in answer.evidence
            ],
        },
    )


BLURRED_BY_DEFAULT = (
    "served and written coordinates are rounded to about a kilometre"
    " unless raw output is asked for explicitly (ADR-0026)"
)


def privacy_payload(report: PrivacyReport) -> dict[str, Any]:
    return named(
        "privacy",
        {
            "photographs": report.photographs,
            "located": report.located,
            "withheld_from_preference": report.withheld_from_preference,
            "stay_captions": report.stay_captions,
            "stay_refused": report.stay_refused,
            "single_captions": report.single_captions,
            "single_refused": report.single_refused,
            "screen_readings": report.screen_readings,
            "screens_label_silent": report.screens_label_silent,
            "subject_readings": report.subject_readings,
            "note_readings": report.note_readings,
            "notes_label_silent": report.notes_label_silent,
            "page_readings": report.page_readings,
            "pages_label_silent": report.pages_label_silent,
            "activity_days": report.activity_days,
            "input_days": report.input_days,
            "kept_profiles": report.kept_profiles,
            "corrections": report.corrections,
            "active_exclusions": report.active_exclusions,
            "never_stored": [name for name, _reason, _test in NEVER_STORED],
            "blurred_by_default": True,
        },
    )


def limits_payload(report: LimitsReport) -> dict[str, Any]:
    """The report as a document, for a tool that acts on it.

    `unseeable` carries the subject and the reason and not the test
    name: a consumer cannot run this repository's tests, and a claim
    is not more true for naming one to a stranger.
    """
    span = report.span
    return named(
        "limits",
        {
            "span": None
            if span is None
            else {
                "first": span.first.isoformat(),
                "last": span.last.isoformat(),
                "days": span.days,
            },
            "sources": [
                {
                    "name": source.name,
                    "count": source.count,
                    "first": None if source.span is None else source.span.first.isoformat(),
                    "last": None if source.span is None else source.span.last.isoformat(),
                    "days": None if source.span is None else source.span.days,
                }
                for source in report.sources
            ],
            "limits": [
                {"subject": limit.subject, "reading": limit.reading, "because": limit.because}
                for limit in report.limits
            ],
            "unseeable": [
                {"subject": subject, "because": reason} for subject, reason, _test in UNSEEABLE
            ],
            "empty": report.empty,
        },
    )


def comparison_payload(comparison: Comparison, blur: bool = True) -> dict[str, Any]:
    return named(
        "compare",
        {
            "before_at": comparison.before_at.isoformat(),
            "after_at": comparison.after_at.isoformat(),
            "entries": [
                {
                    "topic": blurred_place(entry.topic) if blur else entry.topic,
                    "change": entry.change.value,
                    "strength_before": entry.strength_before,
                    "strength_after": entry.strength_after,
                    "evidence_before": entry.evidence_before,
                    "evidence_after": entry.evidence_after,
                    "evidence_refs": [
                        blurred_place(reference) if blur else reference
                        for reference in entry.evidence_refs
                    ],
                }
                for entry in comparison.entries
            ],
        },
    )


def discovery_payload(feed: DiscoveryFeed, blur: bool = True) -> dict[str, Any]:
    return named(
        "discover",
        {
            "oldest_at": feed.oldest_at.isoformat(),
            "latest_at": feed.latest_at.isoformat(),
            "discoveries": [
                {
                    "topic": blurred_place(entry.topic) if blur else entry.topic,
                    "kind": entry.kind.value,
                    "magnitude": entry.magnitude,
                    "confidence": entry.confidence,
                    "evidence": [
                        blurred_place(reference) if blur else reference
                        for reference in entry.evidence
                    ],
                    "novelty": entry.novelty,
                    "importance": entry.importance,
                }
                for entry in feed.entries
            ],
        },
    )


def insights_payload(report: InsightReport, blur: bool = True) -> dict[str, Any]:
    return named(
        "insights",
        {
            "oldest_at": report.oldest_at.isoformat(),
            "latest_at": report.latest_at.isoformat(),
            "insights": [
                {
                    "topic": blurred_place(item.topic) if blur else item.topic,
                    "kind": item.kind.value,
                    "direction": item.direction.value,
                    "magnitude": item.magnitude,
                    "first_seen": item.first_seen.isoformat() if item.first_seen else None,
                    "last_seen": item.last_seen.isoformat() if item.last_seen else None,
                    "confidence": item.confidence,
                    "evidence": [
                        blurred_place(reference) if blur else reference
                        for reference in item.evidence
                    ],
                    "novelty": item.novelty,
                    "derived_from": list(item.derived_from),
                }
                for item in report.insights
            ],
            "mixed": [
                {
                    "held": blurred_place(pair.held) if blur else pair.held,
                    "held_strength": pair.held_strength,
                    "rising": blurred_place(pair.rising) if blur else pair.rising,
                    "rising_magnitude": pair.rising_magnitude,
                }
                for pair in derive_mixed(report)
            ],
        },
    )


def lifecycle_payload(report: LifecycleReport, blur: bool = True) -> dict[str, Any]:
    return named(
        "lifecycle",
        {
            "oldest_at": report.oldest_at.isoformat(),
            "latest_at": report.latest_at.isoformat(),
            "lifecycles": [
                {
                    "topic": blurred_place(item.topic) if blur else item.topic,
                    "stage": item.stage.value,
                    "strength": item.strength,
                    "baseline": item.baseline,
                    "seen_profiles": item.seen_profiles,
                }
                for item in report.lifecycles
            ],
        },
    )


def blurred_place(reference: str) -> str:
    """The blurred form of a place reference; anything else passes."""
    return _blur_place(reference, blur=True)


def blur_radius_m(latitude: float, longitude: float) -> float:
    """How far the true point can be from the blurred one, in metres.

    Blurring rounds each coordinate to `BLUR_DECIMALS` places, so the
    true point lies anywhere in a cell of that size: within half a
    cell **on each axis at once**. The honest radius is therefore the
    distance to the cell's *corner*, not half its height.

    The difference is not pedantic. A consumer drawing the circle
    from the visible decimals computed half the north-south cell --
    553 m at latitude 34.7 -- where the corner is 721 m. A circle
    that small says the point is nearer than the blur promises,
    which is the figure making a claim of its own. Only this library
    knows `BLUR_DECIMALS`, so only this library can say.

    Measured with the library's own haversine rather than a metres-
    per-degree constant, so it is right at any latitude and cannot
    drift from how distance is measured everywhere else."""
    half = 0.5 * 10.0**-BLUR_DECIMALS
    centre = GeoPoint(round(latitude, BLUR_DECIMALS), round(longitude, BLUR_DECIMALS))
    # Near a pole the corner would leave the sphere; the cell is
    # still a cell, so the corner is taken on the side that fits.
    lifted = centre.latitude + half
    corner = GeoPoint(
        lifted if lifted <= 90.0 else centre.latitude - half,
        centre.longitude + half if centre.longitude + half <= 180.0 else centre.longitude - half,
    )
    return centre.distance_to(corner).meters


def _blur_value(value: float, blur: bool) -> float:
    return round(value, BLUR_DECIMALS) if blur else value


def _blur_place(reference: str, blur: bool) -> str:
    """Coarsen a place reference; anything else passes through.

    A reference that looks like a place but cannot be parsed is left
    alone rather than guessed at.
    """
    if not blur or not reference.startswith(PLACE_PREFIX):
        return reference
    latitude_text, separator, longitude_text = reference[len(PLACE_PREFIX) :].partition(",")
    if not separator:
        return reference
    try:
        latitude = float(latitude_text)
        longitude = float(longitude_text)
    except ValueError:
        return reference
    return f"{PLACE_PREFIX}{latitude:.{BLUR_DECIMALS}f},{longitude:.{BLUR_DECIMALS}f}"


def _suggestion(item: Suggestion, blur: bool) -> dict[str, Any]:
    return {
        "kind": item.kind.value,
        "reference": _blur_place(item.reference, blur),
        "confidence": item.confidence,
        "days_since": item.days_since,
        "cadence_days": item.cadence_days,
        "seen_profiles": item.seen_profiles,
        "baseline": item.baseline,
        "distance_km": item.distance_km,
    }


def suggest_payload(found: SuggestionSet, blur: bool = True) -> dict[str, Any]:
    """What `suggest` says, as a document. References are places, so
    they are blurred unless raw is asked for, like every sibling."""
    return named(
        "suggest",
        {
            "suggestions": [_suggestion(item, blur) for item in found.suggestions],
            "day_trips": [_suggestion(item, blur) for item in found.day_trips],
            "reach": None
            if found.reach is None
            else {
                "outings": found.reach.outings,
                "typical_km": found.reach.typical_km,
                "usual_km": found.reach.usual_km,
                "share": found.reach.share,
            },
        },
    )


def narration_payload(narration: Narration) -> dict[str, Any]:
    """The story, and the facts its footnotes point at.

    Each fact is the exact string the model was shown, numbered as it
    was in the prompt, so `[F3]` in the story is `facts[2]` here. The
    facts carry no coordinate by construction: a place is a name from
    the owner's gazetteer or a number, never where it is (ADR-0040)."""
    return named(
        "tell",
        {
            "story": narration.story,
            "facts": [{"id": label, "text": fact} for label, fact in narration.numbered],
        },
    )


def places_payload(
    places: Sequence[PlaceProfile],
    names: Mapping[str, str] | None = None,
    blur: bool = True,
    today: datetime | None = None,
) -> dict[str, Any]:
    """Every place the journeys know, for a map that draws no tiles.

    `blur_radius_m` is the point of it. A consumer that has only the
    coordinate can draw a dot, and a dot says *here*; with the radius
    it can draw the circle the blur actually promises. The number is
    the library's, because the blur is (ADR-0026).

    `days_since` is here rather than left to the reader. A consumer can
    subtract `last_seen` from today, and doing so gives a different
    number: `last_seen` is published as a date while `/suggest` counts
    from the moment, so a place last visited late in the evening reads
    645 days on one card and 646 on the other. Same arithmetic, one
    place, so the two surfaces cannot disagree.

    `name` is resolved from the owner's own gazetteer at display time
    and is a name or nothing -- never a coordinate (ADR-0040)."""
    resolved = names or {}
    now = today if today is not None else datetime.now().astimezone()
    return named(
        "places",
        {
            "blurred": blur,
            "places": [
                {
                    "name": resolved.get(_reference_of(place)),
                    "reference": _blur_place(_reference_of(place), blur),
                    "lat": _blur_value(place.centroid.latitude, blur),
                    "lon": _blur_value(place.centroid.longitude, blur),
                    "blur_radius_m": (
                        round(blur_radius_m(place.centroid.latitude, place.centroid.longitude))
                        if blur
                        else 0
                    ),
                    "visits": place.visits,
                    "trip_visits": place.trip_visits,
                    "first_seen": place.first_seen.date().isoformat(),
                    "last_seen": place.last_seen.date().isoformat(),
                    "cadence_days": place.median_gap_days,
                    "days_since": (naive(now) - naive(place.last_seen)).days,
                }
                for place in places
            ],
        },
    )


def _reference_of(place: PlaceProfile) -> str:
    """The `place:lat,lon` handle, unblurred, as the rest of the
    library writes it."""
    return f"{PLACE_PREFIX}{place.centroid.latitude:.5f},{place.centroid.longitude:.5f}"


def paths_payload(paths: StoragePaths, set_aside: Sequence[str] = ()) -> dict[str, Any]:
    """Where everything is, and which of it the root does not hold.

    Written for the question *can I delete this profile by deleting one
    folder?*, which a person cannot answer by reading seven lines and
    is easy to get wrong: this library's own development root is
    `F:/kiseki-data` with the database on `C:`, so deleting the folder
    would leave the database behind.

    `outside_root` is the answer. Empty means the root holds
    everything and one deletion is enough; anything in it must be
    dealt with separately, and is named so a person can be shown
    what and why."""
    every = {name: str(value) for name, value in vars(paths).items()}
    root = paths.data_root.resolve()
    outside = []
    for name, value in vars(paths).items():
        if name == "data_root":
            continue
        try:
            pathlib.Path(value).resolve().relative_to(root)
        except ValueError:
            outside.append(name)
    return named(
        "paths",
        {
            **every,
            "outside_root": outside,
            "set_aside": list(set_aside),
        },
    )


def today_payload(items: Sequence[Today], blur: bool = True) -> dict[str, Any]:
    """What is worth knowing now, each item saying why.

    `why_today` is a sentence a reader can put on a card without
    rewriting it, and `source` is the command that says the whole of
    the thing, for a reader who disagrees with the choosing. A topic
    can be a place, so it is blurred like every other topic."""
    return named(
        "today",
        {
            "today": [
                {
                    "kind": item.kind,
                    "topic": _blur_place(item.topic, blur),
                    "why_today": item.why_today,
                    "source": item.source,
                }
                for item in items
            ],
        },
    )


def now_payload(screen: Now, blur: bool = True) -> dict[str, Any]:
    """The whole screen as a document.

    `unread` is the part worth reading: a region absent from it is
    full, and a region in it says which command would fill it. A
    consumer can therefore tell *nothing to show* from *nothing was
    ever read*, which a blank region cannot."""
    return named(
        "now",
        {
            "at": screen.at.isoformat(),
            "photographs": screen.photographs,
            "outings": screen.outings,
            "today": today_payload(screen.today, blur=blur)["today"],
            "changed": [
                {
                    "topic": _blur_place(trend.topic, blur),
                    "direction": trend.direction.value,
                    "strength": trend.strength,
                    "baseline": trend.baseline,
                }
                for trend in screen.changed
            ],
            "thin": [
                {"subject": limit.subject, "reading": limit.reading, "because": limit.because}
                for limit in screen.thin
            ],
            "wrong": list(screen.wrong),
            "unread": dict(screen.unread),
        },
    )


def errors_payload() -> dict[str, Any]:
    """Every named way a command can stop.

    Written for an orchestrator that folds failures across seven
    libraries and must say what a name means without a person having
    transcribed it. `retryable` is the field only this library can
    fill: a consumer inferring it from the outcome is guessing.

    `by` carries the library and its version, so that a consumer
    holding a copy of these codes can say which release it copied.

    Two names, and on purpose. `contract` is what the family calls
    this document and what six other libraries answer with; `schema`
    and `version` are how every document here names itself
    (ADR-0081). The version inside the contract name *is* the served
    version, so the two cannot drift.
    """
    return named(
        "errors",
        {
            "contract": CONTRACT.format(version=SERVED_VERSION),
            "by": f"kiseki/{_installed_version()}",
            "errors": [
                {
                    "kind": failure.kind,
                    "exit_code": failure.exit_code,
                    "outcome": failure.outcome,
                    "retryable": failure.retryable,
                    "detail": failure.detail,
                    "detail_ja": failure.detail_ja,
                }
                for failure in CATALOGUE
            ],
            "open_namespaces": list(OPEN_NAMESPACES),
        },
    )
