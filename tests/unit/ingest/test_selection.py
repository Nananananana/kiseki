"""Specification for exclusion patterns."""

from pathlib import Path

import pytest
from kiseki_ingest.selection import is_excluded, relative_to


class TestIsExcluded:
    def test_no_patterns_excludes_nothing(self) -> None:
        assert not is_excluded("photos/IMG_1.jpg", [])

    def test_matches_a_leading_directory(self) -> None:
        assert is_excluded("WhatsApp/IMG_1.jpg", ["WhatsApp*"])

    def test_matches_a_file_name_anywhere(self) -> None:
        assert is_excluded("photos/WhatsApp Image.jpg", ["WhatsApp*"])

    def test_matches_an_extension_at_any_depth(self) -> None:
        assert is_excluded("a/b/c/shot.png", ["*.png"])

    def test_a_star_crosses_directory_separators(self) -> None:
        """``backup/*`` is meant to exclude everything under backup."""
        assert is_excluded("backup/2020/a.jpg", ["backup/*"])

    def test_leaves_non_matching_paths_alone(self) -> None:
        assert not is_excluded("photos/a.jpg", ["*.png", "WhatsApp*"])

    def test_any_pattern_may_match(self) -> None:
        assert is_excluded("Screenshot_1.png", ["*.tmp", "Screenshot_*"])


class TestRelativeTo:
    def test_uses_forward_slashes(self) -> None:
        root = Path("C:/dev/data") if Path("C:/").drive else Path("/data")
        assert relative_to(root, root / "a" / "b.jpg") == "a/b.jpg"

    def test_rejects_a_path_outside_the_root(self) -> None:
        with pytest.raises(ValueError):
            relative_to(Path("/data"), Path("/elsewhere/a.jpg"))
