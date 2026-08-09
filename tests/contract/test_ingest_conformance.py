"""The reference producer must satisfy the contract it ships with."""

import json
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fixtures.synthetic import write_photo, write_screenshot
from kiseki_conformance import PhotoRecordConformance, check_semantics, validate_document
from kiseki_ingest.cli import RECORDS_FILE, SKIPPED_FILE, main
from kiseki_ingest.records import Consent, Owner, build_record, hash_file
from PIL import Image

JST = timezone(timedelta(hours=9))
OWNER = Owner("u1", "d1", "ios")
CONSENT = Consent(use_for_preference=True, use_for_story=True)
BASE_ARGS = ["--owner", "u1", "--default-offset", "+09:00"]


def build(path: Path, thumbnails: Path) -> dict[str, Any]:
    return build_record(
        path,
        owner=OWNER,
        consent=CONSENT,
        default_offset=JST,
        thumbnail_root=thumbnails,
    )


def read_document(output: Path) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads((output / RECORDS_FILE).read_text(encoding="utf-8"))
    return payload


def read_skipped(output: Path) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = json.loads((output / SKIPPED_FILE).read_text(encoding="utf-8"))
    return payload


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

    def test_classifies_a_camera_photograph(self, library: Path, tmp_path: Path) -> None:
        assert build(library / "kyoto.jpg", tmp_path / "thumbs")["content_kind"] == "photo"

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


class TestCli:
    def test_writes_a_document_and_a_skip_report(self, library: Path, tmp_path: Path) -> None:
        output = tmp_path / "out"
        assert main([str(library), str(output), *BASE_ARGS]) == EXIT_OK
        assert len(read_document(output)["records"]) == 4
        assert read_skipped(output)

    def test_reports_a_missing_source(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / "absent"), str(tmp_path / "out"), *BASE_ARGS]) == 2

    def test_skips_a_duplicate_of_an_earlier_file(self, library: Path, tmp_path: Path) -> None:
        """Exports routinely contain the same photograph more than once."""
        copy = library / "kyoto_copy.jpg"
        copy.write_bytes((library / "kyoto.jpg").read_bytes())
        output = tmp_path / "out"

        main([str(library), str(output), *BASE_ARGS])

        assert len(read_document(output)["records"]) == 4
        assert any("identical content" in item["reason"] for item in read_skipped(output))

    def test_applies_an_exclusion_pattern(self, library: Path, tmp_path: Path) -> None:
        output = tmp_path / "out"
        main([str(library), str(output), *BASE_ARGS, "--exclude", "santiago*"])

        captured = [record["captured_at"] for record in read_document(output)["records"]]
        assert not any(moment.startswith("2025-01") for moment in captured)
        assert any("excluded by pattern" in item["reason"] for item in read_skipped(output))

    def test_photos_only_drops_other_content(self, library: Path, tmp_path: Path) -> None:
        write_photo(
            library / "saved.jpg",
            captured_at=datetime(2025, 5, 3, 15, 0, 0),
            offset="+09:00",
            make=None,
            model=None,
        )
        output = tmp_path / "out"
        main([str(library), str(output), *BASE_ARGS, "--photos-only"])

        kinds = {record["content_kind"] for record in read_document(output)["records"]}
        assert kinds == {"photo"}
        assert any("classified as other" in item["reason"] for item in read_skipped(output))


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


EXIT_OK = 0
