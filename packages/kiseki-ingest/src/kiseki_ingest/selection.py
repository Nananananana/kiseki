"""Choosing which files take part in an import run."""

from collections.abc import Sequence
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath


def relative_to(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def is_excluded(relative_path: str, patterns: Sequence[str]) -> bool:
    """Match a glob against the whole relative path, or against the file name alone.

    A star crosses directory separators, so ``backup/*`` excludes everything
    below ``backup``. Matching the bare name as well means ``*.png`` works
    without the caller having to know how deep the file sits.
    """
    posix = PurePosixPath(relative_path).as_posix()
    name = PurePosixPath(relative_path).name
    return any(fnmatch(posix, pattern) or fnmatch(name, pattern) for pattern in patterns)
