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


def resolve_paths(
    overrides: dict[str, str] | None = None, dotenv: Path | None = None
) -> StoragePaths:
    """Work out where everything goes, applying each source in turn."""
    layers: dict[str, str] = {}
    if dotenv is not None:
        layers.update(_from_toml(dotenv.parent / "kiseki.toml"))
        layers.update(_from_dotenv(dotenv))
    layers.update(_from_environment())
    layers.update({key: value for key, value in (overrides or {}).items() if value})

    root = Path(layers.get("data_root", str(default_root()))).expanduser()
    named = {key: Path(layers[key]).expanduser() for key in OVERRIDABLE if key in layers}
    return StoragePaths.derive(root, named)
