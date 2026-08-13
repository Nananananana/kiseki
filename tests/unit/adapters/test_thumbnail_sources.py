"""Both thumbnail sources resolve a reference to bytes, or say why not."""

from pathlib import Path

import pytest

from kiseki.adapters.fake.thumbnails import FakeThumbnailSource
from kiseki.adapters.filesystem.thumbnails import FilesystemThumbnailSource
from kiseki.ports.thumbnails import ThumbnailMissingError


class TestFakeThumbnailSource:
    def test_returns_what_it_was_given(self) -> None:
        source = FakeThumbnailSource({"2025/05/aa.jpg": b"pixels"})
        assert source.read("2025/05/aa.jpg") == b"pixels"

    def test_a_missing_reference_is_an_error(self) -> None:
        with pytest.raises(ThumbnailMissingError):
            FakeThumbnailSource({}).read("2025/05/aa.jpg")


class TestFilesystemThumbnailSource:
    def test_resolves_a_nested_reference_against_the_root(self, tmp_path: Path) -> None:
        (tmp_path / "2025" / "05").mkdir(parents=True)
        (tmp_path / "2025" / "05" / "aa.jpg").write_bytes(b"pixels")
        source = FilesystemThumbnailSource(tmp_path)
        assert source.read("2025/05/aa.jpg") == b"pixels"

    def test_a_missing_file_is_an_error(self, tmp_path: Path) -> None:
        with pytest.raises(ThumbnailMissingError):
            FilesystemThumbnailSource(tmp_path).read("2025/05/aa.jpg")

    def test_a_reference_escaping_the_root_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "thumbs"
        root.mkdir()
        (tmp_path / "secret.txt").write_bytes(b"private")
        with pytest.raises(ThumbnailMissingError):
            FilesystemThumbnailSource(root).read("../secret.txt")
