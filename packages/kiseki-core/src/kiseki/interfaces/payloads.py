"""JSON shapes for what the library measures and reads.

One place builds every payload, so the command line and the HTTP
server cannot drift apart. Blurring lives here because the payloads
are where coordinates become visible: served output blurs by default
(ADR-0026), while the local command line shows what is stored.
"""

from __future__ import annotations

from typing import Any

from kiseki.application.pipeline import Report
from kiseki.domain.interests import Profile
from kiseki.domain.trends import TrendReport

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
