"""Non-photographs without a capture time may borrow the file's.

The contract refuses guessed timestamps; a file's modified time is
not a guess but a measured filesystem fact, carried with its offset
and declared in extra.time_source. The borrowing is opt-in and never
applies to a photograph -- on a camera file the absence of
DateTimeOriginal is an anomaly, not a norm. See ADR-0029.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image

from kiseki_ingest.classification import SCREENSHOT, MediaEvidence, classify
from kiseki_ingest.cli import main
from kiseki_ingest.exif import parse_offset
from kiseki_ingest.records import Consent, Owner, build_record

OFFSET = parse_offset("+09:00")
OWNER = Owner("tester")
CONSENT = Consent(use_for_preference=True, use_for_story=True)
MODIFIED = 1_750_000_000


def _screen_png(path: Path) -> None:
    """A screenshot-shaped PNG with no EXIF, at a known modified time."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1080, 2340), "white").save(path)
    os.utime(path, (MODIFIED, MODIFIED))


def _camera_jpg_without_time(path: Path) -> None:
    """Camera metadata but no DateTimeOriginal: an anomaly, not a norm."""
    path.parent.mkdir(parents=True, exist_ok=True)
    exif = Image.Exif()
    exif[271] = "TestMake"
    Image.new("RGB", (400, 300), "white").save(path, exif=exif)
    os.utime(path, (MODIFIED, MODIFIED))


class TestTimeFallback:
    def test_a_screenshot_borrows_the_file_time(self, tmp_path: Path) -> None:
        source = tmp_path / "Screenshot_001.png"
        _screen_png(source)
        record = build_record(
            source,
            owner=OWNER,
            consent=CONSENT,
            default_offset=OFFSET,
            thumbnail_root=tmp_path / "thumbs",
            mtime_fallback=True,
        )
        assert record["content_kind"] == "screenshot"
        expected = datetime.fromtimestamp(MODIFIED).astimezone()
        assert datetime.fromisoformat(record["captured_at"]) == expected
        assert record["extra"]["time_source"] == "file-modified"

    def test_without_the_fallback_it_is_still_skipped(self, tmp_path: Path) -> None:
        source = tmp_path / "Screenshot_001.png"
        _screen_png(source)
        with pytest.raises(ValueError):
            build_record(
                source,
                owner=OWNER,
                consent=CONSENT,
                default_offset=OFFSET,
                thumbnail_root=tmp_path / "thumbs",
            )

    def test_a_photograph_never_borrows(self, tmp_path: Path) -> None:
        source = tmp_path / "IMG_0001.JPG"
        _camera_jpg_without_time(source)
        with pytest.raises(ValueError):
            build_record(
                source,
                owner=OWNER,
                consent=CONSENT,
                default_offset=OFFSET,
                thumbnail_root=tmp_path / "thumbs",
                mtime_fallback=True,
            )


class TestJapaneseScreenshotNames:
    def test_the_pattern_survives_encoding_accidents(self) -> None:
        """The Japanese screenshot prefix is pinned so a cp932 mishap
        in the source file cannot silently break it again."""
        evidence = MediaEvidence(
            filename="繧ｹ繧ｯ繝ｪ繝ｼ繝ｳ繧ｷ繝ｧ繝・ヨ 2026-08-15 10.00.00.png",
            suffix=".png",
            has_camera_metadata=False,
        )
        assert classify(evidence) == SCREENSHOT


class TestCliFlag:
    def test_the_flag_lets_a_screenshot_in(self, tmp_path: Path) -> None:
        source_dir = tmp_path / "src"
        _screen_png(source_dir / "Screenshot_001.png")
        output = tmp_path / "out"
        code = main(
            [
                str(source_dir),
                str(output),
                "--owner",
                "tester",
                "--default-offset",
                "+09:00",
                "--time-fallback-mtime",
            ]
        )
        assert code == 0
        document = json.loads((output / "photo-records.json").read_text(encoding="utf-8"))
        assert len(document["records"]) == 1
        assert document["records"][0]["content_kind"] == "screenshot"

    def test_without_the_flag_it_is_still_skipped(self, tmp_path: Path) -> None:
        source_dir = tmp_path / "src"
        _screen_png(source_dir / "Screenshot_001.png")
        output = tmp_path / "out"
        assert (
            main(
                [
                    str(source_dir),
                    str(output),
                    "--owner",
                    "tester",
                    "--default-offset",
                    "+09:00",
                ]
            )
            == 0
        )
        document = json.loads((output / "photo-records.json").read_text(encoding="utf-8"))
        assert document["records"] == []
        skipped = json.loads((output / "skipped.json").read_text(encoding="utf-8"))
        assert len(skipped) == 1
