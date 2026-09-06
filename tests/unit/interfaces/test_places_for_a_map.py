"""`/places` and `places --json`: a map that can draw the blur.

A consumer with only the coordinate draws a dot, and a dot says *here*.
The radius is the library's to give, because the blur is.
"""

import json
import os
from datetime import UTC, datetime
from math import hypot
from pathlib import Path

import pytest
from kiseki.domain.services.place_reading import PlaceProfile
from kiseki.domain.shared.geo import GeoPoint
from kiseki.interfaces.cli import EXIT_OK, main
from kiseki.interfaces.payloads import BLUR_DECIMALS, blur_radius_m, places_payload

WHEN = datetime(2026, 3, 1, tzinfo=UTC)
LATER = datetime(2026, 9, 1, tzinfo=UTC)


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _place(latitude: float = 34.70123, longitude: float = 135.50456) -> PlaceProfile:
    return PlaceProfile(
        centroid=GeoPoint(latitude, longitude),
        visits=27,
        first_seen=WHEN,
        last_seen=LATER,
        median_gap_days=12,
    )


class TestTheRadiusIsHonest:
    def test_it_is_the_corner_and_not_the_half_cell(self) -> None:
        """Rounding puts the true point within half a cell on **each**
        axis, so the corner is the reachable worst case. A consumer
        computed half the north-south cell -- 553 m at latitude 34.7 --
        and drew a circle a third too small."""
        half_cell_north_south = GeoPoint(34.70, 135.50).distance_to(GeoPoint(34.705, 135.50)).meters
        radius = blur_radius_m(34.70123, 135.50456)
        assert radius > half_cell_north_south
        assert 700 < radius < 740, radius

    def test_it_matches_the_two_axes_it_is_built_from(self) -> None:
        centre = GeoPoint(34.70, 135.50)
        north = centre.distance_to(GeoPoint(34.705, 135.50)).meters
        east = centre.distance_to(GeoPoint(34.70, 135.505)).meters
        assert blur_radius_m(34.70123, 135.50456) == pytest.approx(hypot(north, east), rel=0.01)

    def test_it_shrinks_with_latitude(self) -> None:
        """A degree of longitude is shorter near the pole, so the cell is
        narrower and the circle smaller. A fixed number would be wrong."""
        assert blur_radius_m(60.0, 0.0) < blur_radius_m(0.0, 0.0)

    def test_it_holds_at_the_pole(self) -> None:
        assert blur_radius_m(89.999, 179.999) > 0

    def test_it_follows_the_blur_and_is_not_a_constant(self) -> None:
        """If BLUR_DECIMALS moves, the radius moves with it, because the
        two are the same fact said twice otherwise."""
        assert BLUR_DECIMALS == 2
        cell = 10.0**-BLUR_DECIMALS
        assert blur_radius_m(0.0, 0.0) < cell * 111_320


class TestThePayload:
    def test_a_place_carries_its_circle_and_its_counts(self) -> None:
        document = places_payload([_place()])
        assert document["schema"] == "kiseki-places"
        assert document["blurred"] is True
        (place,) = document["places"]
        assert place["lat"] == 34.7
        assert place["lon"] == 135.5
        assert 700 < place["blur_radius_m"] < 740
        assert place["visits"] == 27
        assert place["cadence_days"] == 12
        assert place["first_seen"] == "2026-03-01"
        assert place["last_seen"] == "2026-09-01"

    def test_raw_says_it_is_not_blurred_and_offers_no_circle(self) -> None:
        document = places_payload([_place()], blur=False)
        assert document["blurred"] is False
        (place,) = document["places"]
        assert place["lat"] == 34.70123
        assert place["blur_radius_m"] == 0, "a raw point is not a circle"

    def test_a_name_is_a_name_and_never_a_coordinate(self) -> None:
        reference = "place:34.70123,135.50456"
        document = places_payload([_place()], names={reference: "Umeda (JP)"})
        assert document["places"][0]["name"] == "Umeda (JP)"

    def test_an_unnamed_place_says_nothing_rather_than_guessing(self) -> None:
        assert places_payload([_place()])["places"][0]["name"] is None

    def test_no_place_is_not_an_error(self) -> None:
        """A library with no photographs has a map that says so."""
        document = places_payload([])
        assert document["places"] == []
        assert document["schema"] == "kiseki-places"


class TestTheCommand:
    def test_places_json_on_an_empty_library_is_a_named_document(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "places", "--json"]) == EXIT_OK
        out = capsys.readouterr().out
        document = json.loads(out[out.index("{") :])
        assert document["schema"] == "kiseki-places"
        assert document["places"] == []
