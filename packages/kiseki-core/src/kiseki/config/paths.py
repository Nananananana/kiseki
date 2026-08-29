"""Where things live.

No absolute path appears anywhere in this project, including the defaults. Where
somebody keeps tens of thousands of photographs is theirs to decide, and often
means a second drive, so every location can be set individually as well as
derived from one root.

Precedence, weakest first: built-in defaults, a kiseki.toml beside the dotenv
file, the dotenv file, the environment, then the command line. The environment
beats the files so that a container or a CI run can override without editing
anything.
"""

import os
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

ENV_PREFIX = "KISEKI_"
DEFAULT_ROOT_NAME = ".kiseki"
OVERRIDABLE = (
    "records_dir",
    "thumbs_dir",
    "db_path",
    "cache_dir",
    "log_dir",
    "gazetteer_path",
)


@dataclass(frozen=True)
class StoragePaths:
    data_root: Path
    records_dir: Path
    thumbs_dir: Path
    db_path: Path
    cache_dir: Path
    log_dir: Path
    gazetteer_path: Path

    @classmethod
    def derive(cls, data_root: Path, overrides: dict[str, Path] | None = None) -> "StoragePaths":
        """Everything follows the root, except what is named explicitly."""
        derived = cls(
            data_root=data_root,
            records_dir=data_root / "records",
            thumbs_dir=data_root / "thumbs",
            db_path=data_root / "db" / "kiseki.sqlite3",
            cache_dir=data_root / "cache",
            log_dir=data_root / "logs",
            gazetteer_path=data_root / "gazetteer" / "cities500.txt",
        )
        return replace(derived, **(overrides or {}))


def default_root() -> Path:
    return Path.home() / DEFAULT_ROOT_NAME


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
    return {key: str(value) for key, value in document.get("paths", {}).items()}


RANK = {"default": 0, "toml": 1, "dotenv": 2, "environment": 3, "command line": 4}
"""How much each source is worth when two of them disagree."""


def _layered(overrides: dict[str, str] | None, dotenv: Path | None) -> dict[str, tuple[str, str]]:
    """Every setting, with the name of the layer that last set it."""
    layers: dict[str, tuple[str, str]] = {}
    if dotenv is not None:
        for key, value in _from_toml(dotenv.parent / "kiseki.toml").items():
            layers[key] = (value, "toml")
        for key, value in _from_dotenv(dotenv).items():
            layers[key] = (value, "dotenv")
    for key, value in _from_environment().items():
        layers[key] = (value, "environment")
    for key, value in (overrides or {}).items():
        if value:
            layers[key] = (value, "command line")
    return layers


def set_aside(
    overrides: dict[str, str] | None = None, dotenv: Path | None = None
) -> tuple[str, ...]:
    """Paths a stronger root displaced, so the caller can say so.

    An explicit path beats a derived one, which is right inside a
    layer and wrong across them: `--data-root` moving the root while
    an .env still named `db_path` meant the flag appeared to work and
    did nothing, and a synthetic corpus went into a real library
    twice before anybody noticed.
    """
    layers = _layered(overrides, dotenv)
    root_rank = RANK[layers.get("data_root", ("", "default"))[1]]
    return tuple(key for key in OVERRIDABLE if key in layers and RANK[layers[key][1]] < root_rank)


def resolve_paths(
    overrides: dict[str, str] | None = None, dotenv: Path | None = None
) -> StoragePaths:
    """Work out where everything goes, applying each source in turn.

    A path named in a layer weaker than the one that named the root is
    set aside: somebody who says where the root is on the command line
    has said where everything goes, and a file cannot answer back.
    """
    layers = _layered(overrides, dotenv)
    root_rank = RANK[layers.get("data_root", ("", "default"))[1]]
    root = Path(layers.get("data_root", (str(default_root()), "default"))[0]).expanduser()
    named = {
        key: Path(layers[key][0]).expanduser()
        for key in OVERRIDABLE
        if key in layers and RANK[layers[key][1]] >= root_rank
    }
    return StoragePaths.derive(root, named)
