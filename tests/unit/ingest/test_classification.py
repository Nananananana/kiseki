"""Specification for content classification."""

import pytest
from kiseki_ingest.classification import MediaEvidence, classify


def evidence(
    filename: str,
    *,
    camera: bool = False,
    width: int | None = None,
    height: int | None = None,
) -> MediaEvidence:
    suffix = filename[filename.rfind(".") :] if "." in filename else ""
    return MediaEvidence(filename, suffix, camera, width, height)


class TestPhotographs:
    def test_camera_metadata_means_a_photograph(self) -> None:
        assert classify(evidence("IMG_1234.HEIC", camera=True, width=4032, height=3024)) == "photo"

    def test_a_photograph_in_a_screen_shape_is_still_a_photograph(self) -> None:
        """A 4:3 photograph shares its ratio with a tablet screen."""
        assert classify(evidence("IMG_1.jpg", camera=True, width=4032, height=3024)) == "photo"


class TestScreenshots:
    @pytest.mark.parametrize(
        "filename",
        [
            "Screenshot_20250503.png",
            "Screen Shot 2025-05-03.png",
            "screen-shot-1.png",
            "スクリーンショット 2025-05-03.png",
            "SCR_0001.png",
        ],
    )
    def test_recognises_common_names(self, filename: str) -> None:
        assert classify(evidence(filename)) == "screenshot"

    def test_recognises_a_phone_screen_shape_without_camera_data(self) -> None:
        assert classify(evidence("untitled.png", width=1170, height=2532)) == "screenshot"

    def test_the_name_wins_over_camera_metadata(self) -> None:
        """An edited screenshot can carry the exporting device's metadata."""
        result = classify(evidence("Screenshot.jpg", camera=True, width=1170, height=2532))
        assert result == "screenshot"


class TestOther:
    def test_a_square_image_is_not_a_screenshot(self) -> None:
        assert classify(evidence("logo.png", width=500, height=500)) == "other"

    def test_an_image_with_no_camera_data_is_other(self) -> None:
        assert classify(evidence("saved.jpg", width=1200, height=800)) == "other"

    def test_missing_dimensions_do_not_imply_a_screenshot(self) -> None:
        assert classify(evidence("a.png")) == "other"

    def test_documents_are_never_assigned_here(self) -> None:
        """A photographed receipt looks exactly like a photograph in metadata."""
        assert classify(evidence("IMG_9999.jpg", camera=True, width=3024, height=4032)) == "photo"
