"""The thresholds a derivation uses, and where a reader changes them.

Ten numbers decide what a stay is, what an outing is, and what a place
returned to is. Five of them were measured (ADR-0006) -- against **one
photo library**: 4,950 photographs, one person, one country, one way
of living. That is more than most such numbers get, and it is still
one library.

Until this module existed there was no way to change any of them.
`kiseki build --help` listed one option, `--help`. Meanwhile
`tools/journeys.py`, the aid built for tuning them, took six as flags.
The tuning existed and never reached the command anybody runs (#387).

## What that costs somebody who is not the developer

    a photographer shooting 200 frames at one spot
        meets min_photographs = 5 continuously; every pause is a stay

    somebody who takes three photographs a week
        never reaches 5, and falls through to min_duration -- a
        different rule, reached by accident rather than by design

    rural life, the shop two kilometres from the house
        one visit split by stay_radius = 300

    a dense city
        three different places merged by cluster_radius = 500

## And one that is not a tuning problem

`night_hours` and `working_hours` describe an office worker's day. An
anchor is deliberately never named -- the design's answer to *is this
a home or a workplace* is that the night share and daytime share speak
for themselves. **For a night-shift worker those two are inverted**,
and the library describes their workplace with the shares that mean
home. The shares speak for themselves in one schedule.

Making it configurable does not fix that. It makes it *possible* to
fix, and says out loud that the default assumed something.

## The layers

The same five as the storage paths, the model host and the algorithm,
because a person who has learned one has learned all four:

    default -> kiseki.toml -> .env -> environment -> command line

An unknown `KISEKI_DERIVATION_*` key is refused rather than ignored. A
typo that silently does nothing leaves a reader believing they changed
something, which is worse than an error and much harder to notice --
`config/model.py` gives the same reason for the same rule.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from kiseki.domain.shared.geo import Distance
from kiseki.domain.shared.settings import (
    AnchorSettings,
    OutingSettings,
    StopSettings,
)
from kiseki.domain.shared.speed import Speed

ENV_PREFIX = "KISEKI_DERIVATION_"

MEASURED = "measured against one photo library (ADR-0006)"
CHOSEN = "chosen, not measured"

KNOWN: dict[str, str] = {
    "stay_radius_m": MEASURED,
    "drift_speed_kmh": MEASURED,
    "max_gap_minutes": MEASURED,
    "min_duration_minutes": MEASURED,
    "min_photographs": MEASURED,
    "max_absence_hours": CHOSEN,
    "cluster_radius_m": CHOSEN,
    "min_visits": CHOSEN,
    "night_hours": CHOSEN,
    "working_hours": CHOSEN,
}
"""Every setting, and how its default came to be that number.

Carried here rather than only in prose because a reader deciding
whether to change one needs to know which kind of number they are
arguing with. Four of the ten are measured; six were chosen."""

UNITS = "the suffix is the unit: _m metres, _kmh km/h, _minutes, _hours"


@dataclass(frozen=True)
class DerivationSettings:
    """The three settings objects, and where each value came from."""

    stops: StopSettings
    outings: OutingSettings
    anchors: AnchorSettings
    sources: dict[str, str]
    """Which layer supplied each value: `default`, `kiseki.toml`,
    `.env`, `environment` or `command line`. Printed by `kiseki
    settings`, because a reader debugging a strange answer needs to
    know whether it is their data or their configuration."""


def _hours(text: str, name: str) -> tuple[int, int]:
    parts = [part.strip() for part in text.replace("-", ",").split(",") if part.strip()]
    if len(parts) != 2:
        raise ValueError(f"{name} takes two hours, like '20,6'. Got {text!r}")
    try:
        start, end = int(parts[0]), int(parts[1])
    except ValueError:
        raise ValueError(f"{name} takes two whole hours, like '20,6'. Got {text!r}") from None
    for hour in (start, end):
        if not 0 <= hour <= 23:
            raise ValueError(f"{name}: {hour} is not an hour of the day")
    return start, end


def _number(text: str, name: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"{name} takes a number. Got {text!r}") from None


def _from_environment() -> dict[str, str]:
    return {
        key[len(ENV_PREFIX) :].lower(): value
        for key, value in os.environ.items()
        if key.startswith(ENV_PREFIX) and value
    }


def _from_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key.startswith(ENV_PREFIX) and value:
            values[key[len(ENV_PREFIX) :].lower()] = value
    return values


def _from_toml(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    document: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    section = document.get("derivation", {})
    return {
        key: ",".join(str(item) for item in value) if isinstance(value, list) else str(value)
        for key, value in section.items()
    }


def resolve_derivation_settings(
    overrides: dict[str, str] | None = None, dotenv: Path | None = None
) -> DerivationSettings:
    """Work out the thresholds, applying each source in turn."""
    layers: dict[str, str] = {}
    sources: dict[str, str] = dict.fromkeys(KNOWN, "default")

    def apply(values: dict[str, str], name: str) -> None:
        for key, value in values.items():
            layers[key] = value
            sources[key] = name

    if dotenv is not None:
        apply(_from_toml(dotenv.parent / "kiseki.toml"), "kiseki.toml")
        apply(_from_dotenv(dotenv), ".env")
    apply(_from_environment(), "environment")
    apply({key: value for key, value in (overrides or {}).items() if value}, "command line")

    unknown = sorted(set(layers) - set(KNOWN))
    if unknown:
        raise ValueError(
            "these derivation settings are not recognised, so they would have done "
            f"nothing: {', '.join(unknown)}. Known settings: {', '.join(KNOWN)}. "
            f"({UNITS})"
        )

    defaults_stops = StopSettings()
    defaults_outings = OutingSettings()
    defaults_anchors = AnchorSettings()

    def metres(key: str, fallback: Distance) -> Distance:
        return Distance(_number(layers[key], key)) if key in layers else fallback

    stops = StopSettings(
        stay_radius=metres("stay_radius_m", defaults_stops.stay_radius),
        drift_speed=(
            Speed.from_kilometers_per_hour(_number(layers["drift_speed_kmh"], "drift_speed_kmh"))
            if "drift_speed_kmh" in layers
            else defaults_stops.drift_speed
        ),
        max_gap=(
            timedelta(minutes=_number(layers["max_gap_minutes"], "max_gap_minutes"))
            if "max_gap_minutes" in layers
            else defaults_stops.max_gap
        ),
        min_duration=(
            timedelta(minutes=_number(layers["min_duration_minutes"], "min_duration_minutes"))
            if "min_duration_minutes" in layers
            else defaults_stops.min_duration
        ),
        min_photographs=(
            int(_number(layers["min_photographs"], "min_photographs"))
            if "min_photographs" in layers
            else defaults_stops.min_photographs
        ),
    )
    outings = OutingSettings(
        max_absence=(
            timedelta(hours=_number(layers["max_absence_hours"], "max_absence_hours"))
            if "max_absence_hours" in layers
            else defaults_outings.max_absence
        )
    )
    anchors = AnchorSettings(
        cluster_radius=metres("cluster_radius_m", defaults_anchors.cluster_radius),
        min_visits=(
            int(_number(layers["min_visits"], "min_visits"))
            if "min_visits" in layers
            else defaults_anchors.min_visits
        ),
        night_hours=(
            _hours(layers["night_hours"], "night_hours")
            if "night_hours" in layers
            else defaults_anchors.night_hours
        ),
        working_hours=(
            _hours(layers["working_hours"], "working_hours")
            if "working_hours" in layers
            else defaults_anchors.working_hours
        ),
    )
    return DerivationSettings(stops, outings, anchors, sources)


def in_force(settings: DerivationSettings) -> list[tuple[str, str, str, str]]:
    """Every setting as (name, value, where it came from, provenance)."""
    stops, outings, anchors = settings.stops, settings.outings, settings.anchors
    values = {
        "stay_radius_m": f"{stops.stay_radius.meters:g}",
        "drift_speed_kmh": f"{stops.drift_speed.meters_per_second * 3.6:g}",
        "max_gap_minutes": f"{stops.max_gap.total_seconds() / 60:g}",
        "min_duration_minutes": f"{stops.min_duration.total_seconds() / 60:g}",
        "min_photographs": str(stops.min_photographs),
        "max_absence_hours": f"{outings.max_absence.total_seconds() / 3600:g}",
        "cluster_radius_m": f"{anchors.cluster_radius.meters:g}",
        "min_visits": str(anchors.min_visits),
        "night_hours": f"{anchors.night_hours[0]},{anchors.night_hours[1]}",
        "working_hours": f"{anchors.working_hours[0]},{anchors.working_hours[1]}",
    }
    return [(name, values[name], settings.sources[name], KNOWN[name]) for name in KNOWN]
