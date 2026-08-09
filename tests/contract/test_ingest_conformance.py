"""The reference producer must satisfy the contract it ships with."""

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fixtures.synthetic import write_photo, write_screenshot
from kiseki_conformance import PhotoRecordConformance, check_semantics, validate_document
from kiseki_ingest.cli import RECORDS_FILE, SKIPPED_FILE, main
from kiseki_ingest.reader import read_exif
from kiseki_ingest.records import Consent, Owner, build_record, classify, hash_file
from PIL import Image

JST = timezone(timedelta(hours=9))
OWNER = Owner("u1", "d1", "ios")
CONSENT = Consent(use_for_preference=True, use_for_story=True)


def build(path: Path, thumbnails: Path) -> dict[str, Any]:
    return build_record(
        path,
        owner=OWNER,
        consent=CONSENT,
        default_offset=JST,
        thumbnail_root=thumbnails,
    )


@pytest.fixture
def library(tmp_path: Path) -> Path:
    """A small photo library covering the cases that actually occur."""
    source = tmp_path / "source"
    write_photo(
        source / "kyoto.jpg",
        captured_at=datetime(2025, 5, 3, 10, 24, 31),
        offset="+09:00",
        latitude=35.0094,
        longitude=135.6669,
    )
    write_photo(
        source / "no_gps.jpg",
        captured_at=datetime(2025, 5, 3, 13, 2, 0),
        offset="+09:00",
    )
    write_photo(
        source / "no_offset.jpg",
        captured_at=datetime(2025, 5, 3, 9, 0, 0),
    )
    write_photo(
        source / "santiago.jpg",
        captured_at=datetime(2025, 1, 2, 3, 4, 5),
        offset="-03:00",
        latitude=-33.4489,
        longitude=-70.6693,
    )
    write_screenshot(source / "screenshot.png")
    return source


class TestBuildRecord:
    def test_reads_time_and_place(self, library: Path, tmp_path: Path) -> None:
        record = build(library / "kyoto.jpg", tmp_path / "thumbs")
        assert record["captured_at"] == "2025-05-03T10:24:31+09:00"
        assert record["location"]["lat"] == pytest.approx(35.0094, abs=1e-4)
        assert record["location_source"] == "measured"

    def test_keeps_a_photo_without_coordinates(self, library: Path, tmp_path: Path) -> None:
        record = build(library / "no_gps.jpg", tmp_path / "thumbs")
        assert record["location"] is None
        assert "location_source" not in record

    def test_applies_the_default_offset(self, library: Path, tmp_path: Path) -> None:
        record = build(library / "no_offset.jpg", tmp_path / "thumbs")
        assert record["captured_at"].endswith("+09:00")

    def test_handles_the_southern_and_western_hemispheres(
        self, library: Path, tmp_path: Path
    ) -> None:
        record = build(library / "santiago.jpg", tmp_path / "thumbs")
        assert record["location"]["lat"] < 0
        assert record["location"]["lon"] < 0
        assert record["captured_at"].endswith("-03:00")

    def test_refuses_a_file_with_no_capture_time(self, library: Path, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="DateTimeOriginal"):
            build(library / "screenshot.png", tmp_path / "thumbs")

    def test_identifier_is_derived_from_content(self, library: Path, tmp_path: Path) -> None:
        first = build(library / "kyoto.jpg", tmp_path / "a")
        second = build(library / "kyoto.jpg", tmp_path / "b")
        assert first["id"] == second["id"]
        assert first["id"] == f"sha256:{hash_file(library / 'kyoto.jpg')}"

    def test_thumbnail_reference_is_relative(self, library: Path, tmp_path: Path) -> None:
        record = build(library / "kyoto.jpg", tmp_path / "thumbs")
        assert not Path(record["thumbnail_ref"]).is_absolute()
        assert record["thumbnail_ref"].startswith("2025/05/")

    def test_thumbnail_is_written_and_bounded(self, library: Path, tmp_path: Path) -> None:
        thumbnails = tmp_path / "thumbs"
        record = build(library / "kyoto.jpg", thumbnails)
        written = thumbnails / record["thumbnail_ref"]
        assert written.exists()
        with Image.open(written) as thumbnail:
            assert max(thumbnail.size) <= 512

    def test_classifies_a_camera_photo(self, library: Path) -> None:
        assert classify(read_exif(library / "kyoto.jpg")) == "photo"


class TestCli:
    def test_writes_a_document_and_a_skip_report(self, library: Path, tmp_path: Path) -> None:
        output = tmp_path / "out"
        code = main([str(library), str(output), "--owner", "u1", "--default-offset", "+09:00"])
        assert code == 0
        assert (output / RECORDS_FILE).exists()
        assert (output / SKIPPED_FILE).exists()

    def test_reports_a_missing_source(self, tmp_path: Path) -> None:
        code = main(
            [
                str(tmp_path / "absent"),
                str(tmp_path / "out"),
                "--owner",
                "u1",
                "--default-offset",
                "+09:00",
            ]
        )
        assert code == 2


class TestProducedDocumentConformance(PhotoRecordConformance):
    """The whole point: what the producer emits passes the published contract."""

    @pytest.fixture
    def document(self, library: Path, tmp_path: Path) -> Mapping[str, Any]:
        thumbnails = tmp_path / "thumbs"
        records = [build(path, thumbnails) for path in sorted(library.glob("*.jpg"))]
        return {"schema_version": "1.0", "records": records}

    def test_reports_no_violations_at_all(self, document: Mapping[str, Any]) -> None:
        assert validate_document(document) == []
        assert check_semantics(document) == []
