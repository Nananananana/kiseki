"""Where the model is, and how far away it is allowed to be.

The adapters have taken a `host` since v0.2 and nothing ever passed
one, so the parameter was a promise nobody could keep. This is the
layer that keeps it: the same precedence as the storage paths --
defaults, `kiseki.toml`, the dotenv file, the environment, the command
line -- because a person who has learned one of them has learned both.

The boundary travels with the host, since a host without one is a
setting that means nothing. See ADR-0073 for what the boundary is and
why the strictest is the default.

An unknown `KISEKI_MODEL_*` key is refused rather than ignored. A typo
in a privacy setting that silently does nothing is the worst available
outcome: the owner believes they narrowed the boundary, and nothing
narrowed.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kiseki.domain.trust import TrustBoundary, Verdict, judge

ENV_PREFIX = "KISEKI_MODEL_"

DEFAULT_PARALLEL = 1
"""One call at a time. Measured on this machine before the setting
existed; the number to raise it to is the server's, not this file's."""

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_CAPTIONING_MODEL = "qwen3-vl:8b"
DEFAULT_LANGUAGE_MODEL = "qwen2.5:14b-instruct-q4_K_M"
DEFAULT_EMBEDDING_MODEL = "bge-m3"

KNOWN = (
    "host",
    "boundary",
    "trusted_hosts",
    "captioning_model",
    "language_model",
    "embedding_model",
    "parallel",
)


@dataclass(frozen=True)
class ModelSettings:
    """Everything about the models, in one object the owner can print."""

    host: str = DEFAULT_HOST
    boundary: TrustBoundary = TrustBoundary.SAME_HOST
    trusted_hosts: tuple[str, ...] = ()
    captioning_model: str = DEFAULT_CAPTIONING_MODEL
    language_model: str = DEFAULT_LANGUAGE_MODEL
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    parallel: int = DEFAULT_PARALLEL
    """How many one-element model calls the captioning loops keep in
    flight at once. One is a plain loop. Set from OLLAMA_NUM_PARALLEL's
    value on the server, not above it: the server queues what it
    cannot run, and the wall-clock gain stops there."""

    def __post_init__(self) -> None:
        if self.parallel < 1:
            raise ValueError(f"parallel must be at least 1, not {self.parallel}")

    @property
    def verdict(self) -> Verdict:
        return judge(self.host, self.boundary, self.trusted_hosts)


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
    section = document.get("model", {})
    return {
        key: ",".join(str(item) for item in value) if isinstance(value, list) else str(value)
        for key, value in section.items()
    }


def resolve_model_settings(
    overrides: dict[str, str] | None = None, dotenv: Path | None = None
) -> ModelSettings:
    """Work out where the model is, applying each source in turn."""
    layers: dict[str, str] = {}
    if dotenv is not None:
        layers.update(_from_toml(dotenv.parent / "kiseki.toml"))
        layers.update(_from_dotenv(dotenv))
    layers.update(_from_environment())
    layers.update({key: value for key, value in (overrides or {}).items() if value})

    unknown = sorted(set(layers) - set(KNOWN))
    if unknown:
        raise ValueError(
            "these model settings are not recognised, so they would have done"
            f" nothing: {', '.join(unknown)}. Known settings: {', '.join(KNOWN)}"
        )

    boundary = TrustBoundary.SAME_HOST
    if "boundary" in layers:
        try:
            boundary = TrustBoundary(layers["boundary"].strip().lower())
        except ValueError:
            allowed = ", ".join(item.value for item in TrustBoundary)
            raise ValueError(
                f"'{layers['boundary']}' is not a trust boundary. Choose one of: {allowed}"
            ) from None

    trusted = tuple(
        name.strip().lower() for name in layers.get("trusted_hosts", "").split(",") if name.strip()
    )
    parallel = DEFAULT_PARALLEL
    if "parallel" in layers:
        try:
            parallel = int(layers["parallel"].strip())
        except ValueError:
            raise ValueError(
                f"'{layers['parallel']}' is not a number of calls to keep in flight"
            ) from None
        if parallel < 1:
            raise ValueError(f"parallel must be at least 1, not {parallel}")
    return ModelSettings(
        host=layers.get("host", DEFAULT_HOST),
        boundary=boundary,
        trusted_hosts=trusted,
        captioning_model=layers.get("captioning_model", DEFAULT_CAPTIONING_MODEL),
        language_model=layers.get("language_model", DEFAULT_LANGUAGE_MODEL),
        embedding_model=layers.get("embedding_model", DEFAULT_EMBEDDING_MODEL),
        parallel=parallel,
    )
