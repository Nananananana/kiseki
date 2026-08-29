"""JSON shapes for what the library measures and reads.

One place builds every payload, so the command line and the HTTP
server cannot drift apart. Blurring lives here because the payloads
are where coordinates become visible: served output blurs by default
(ADR-0026), while the local command line shows what is stored.
"""

from __future__ import annotations

from typing import Any

from kiseki.application.asking import Answer
from kiseki.application.pipeline import PrivacyReport, Report
from kiseki.domain.comparison import Comparison
from kiseki.domain.discovery import DiscoveryFeed
from kiseki.domain.insight import InsightReport
from kiseki.domain.interests import Profile
from kiseki.domain.lifecycle import LifecycleReport
from kiseki.domain.services.mixing import derive_mixed
from kiseki.domain.trends import TrendReport
from kiseki.interfaces.claims import NEVER_STORED

BLUR_DECIMALS = 2
"""Decimal places kept when blurring: roughly a kilometre grid,
enough to say "around here" without saying "this doorstep"."""

PLACE_PREFIX = "place:"


def report_payload(report: Report, blur: bool = False) -> dict[str, Any]:
    habits = report.habits
    return {
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
    }


def profile_payload(profile: Profile, blur: bool = False) -> dict[str, Any]:
    return {
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
    }


def trend_payload(report: TrendReport, blur: bool = False) -> dict[str, Any]:
    return {
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
    }


def answer_payload(answer: Answer, blur: bool = False) -> dict[str, Any]:
    return {
        "question": answer.question,
        "answer": answer.answer if answer.answered else None,
        "confidence": answer.confidence,
        "first_seen": answer.first_seen.isoformat() if answer.first_seen else None,
        "last_seen": answer.last_seen.isoformat() if answer.last_seen else None,
        "model": answer.model,
        "since": answer.since.isoformat() if answer.since else None,
        "until": answer.until.isoformat() if answer.until else None,
        "supporting_insights": [
            {
                "topic": item.topic,
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
    }


BLURRED_BY_DEFAULT = (
    "served and written coordinates are rounded to about a kilometre"
    " unless raw output is asked for explicitly (ADR-0026)"
)


def privacy_payload(report: PrivacyReport) -> dict[str, Any]:
    return {
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
        "kept_profiles": report.kept_profiles,
        "corrections": report.corrections,
        "active_exclusions": report.active_exclusions,
        "never_stored": [name for name, _reason, _test in NEVER_STORED],
        "blurred_by_default": True,
    }


def comparison_payload(comparison: Comparison, blur: bool = False) -> dict[str, Any]:
    return {
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
    }


def discovery_payload(feed: DiscoveryFeed, blur: bool = False) -> dict[str, Any]:
    return {
        "oldest_at": feed.oldest_at.isoformat(),
        "latest_at": feed.latest_at.isoformat(),
        "discoveries": [
            {
                "topic": blurred_place(entry.topic) if blur else entry.topic,
                "kind": entry.kind.value,
                "magnitude": entry.magnitude,
                "confidence": entry.confidence,
                "evidence": [
                    blurred_place(reference) if blur else reference for reference in entry.evidence
                ],
                "novelty": entry.novelty,
                "importance": entry.importance,
            }
            for entry in feed.entries
        ],
    }


def insights_payload(report: InsightReport, blur: bool = False) -> dict[str, Any]:
    return {
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
                    blurred_place(reference) if blur else reference for reference in item.evidence
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
    }


def lifecycle_payload(report: LifecycleReport, blur: bool = False) -> dict[str, Any]:
    return {
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
    }


def blurred_place(reference: str) -> str:
    """The blurred form of a place reference; anything else passes."""
    return _blur_place(reference, blur=True)


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
