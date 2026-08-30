"""The version a wheel would carry is the version that was released.

`packages/kiseki-core/pyproject.toml` said 0.4.0 while `docs/releases/` held
six later versions, because a release changes the README and the release note
and nothing has ever built a wheel. Anybody installing from this tree would
have been told 0.4.0, and the person who noticed would have been a stranger.

Nothing else about this file's contents is asserted here. `kiseki-core`
declares no runtime dependency, and that claim is checked where it is a fact
rather than a declaration -- against the `Requires-Dist` of a built wheel, in
`tools/check_packaging.py`. Two tests of different strength asserting one fact
are worse than one: the weaker is what a reader finds first, and it looks like
coverage.
"""

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
CORE = REPO_ROOT / "packages" / "kiseki-core" / "pyproject.toml"
RELEASES = REPO_ROOT / "docs" / "releases"


def as_numbers(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def released_versions() -> list[tuple[int, ...]]:
    found = [as_numbers(path.stem.lstrip("v")) for path in RELEASES.glob("v*.md")]
    assert found, "docs/releases holds no release notes"
    return found


def distribution_version() -> tuple[int, ...]:
    project: dict[str, str] = tomllib.loads(CORE.read_text(encoding="utf-8"))["project"]
    return as_numbers(project["version"])


def test_the_distribution_version_is_the_one_that_was_released() -> None:
    assert distribution_version() == max(released_versions()), (
        "packages/kiseki-core/pyproject.toml and docs/releases disagree about "
        "which version this is. A release bumps both."
    )
