"""Which algorithm decided this, and where that decision is written.

The same precedence as the storage paths and the model host --
defaults, `kiseki.toml`, the dotenv file, the environment, the command
line -- because a person who has learned one of them has learned all
three. See `docs/algorithms.md` for what the choices are.

An unknown `KISEKI_ALGORITHM_*` key is refused rather than ignored,
for the reason the model settings give: a typo that silently does
nothing leaves the owner believing they changed something.

A detector **name** that is not recognised is refused too, and never
falls back to the default. A reader who mistyped an algorithm and got
the default would be told their answers came from a detector they did
not choose, which is worse than an error and much harder to notice.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kiseki.adapters.clustering import detector_named, every_name
from kiseki.domain.services.detectors import DEFAULT_DETECTOR, StopDetector

ENV_PREFIX = "KISEKI_ALGORITHM_"

KNOWN = ("stops",)
"""One setting so far. The list exists because the refusal above needs
something to be a list of, and because the second one will be added
here rather than somewhere else."""


@dataclass(frozen=True)
class AlgorithmSettings:
    """Which algorithm each derivation uses."""

    stops: str = DEFAULT_DETECTOR

    @property
    def stop_detector(self) -> StopDetector:
        return detector_named(self.stops)


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
    section = document.get("algorithm", {})
    return {key: str(value) for key, value in section.items()}


def resolve_algorithm_settings(
    overrides: dict[str, str] | None = None, dotenv: Path | None = None
) -> AlgorithmSettings:
    """Work out which algorithms to use, applying each source in turn."""
    layers: dict[str, str] = {}
    if dotenv is not None:
        layers.update(_from_toml(dotenv.parent / "kiseki.toml"))
        layers.update(_from_dotenv(dotenv))
    layers.update(_from_environment())
    layers.update({key: value for key, value in (overrides or {}).items() if value})

    unknown = sorted(set(layers) - set(KNOWN))
    if unknown:
        raise ValueError(
            "these algorithm settings are not recognised, so they would have done"
            f" nothing: {', '.join(unknown)}. Known settings: {', '.join(KNOWN)}"
        )

    stops = layers.get("stops", DEFAULT_DETECTOR).strip()
    if stops not in every_name():
        raise ValueError(
            f"{stops!r} is not a stop detector. Choose one of: {', '.join(every_name())}"
        )
    return AlgorithmSettings(stops=stops)
