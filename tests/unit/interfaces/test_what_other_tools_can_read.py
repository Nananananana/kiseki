"""The interchange formats, checked by the libraries that read them.

A format is a promise to somebody else's program, so a test that only
runs this repository's own parser is a test of nothing: it would agree
with any consistent mistake. These read the output with **shapely**
and **pandas**, which is what a reader would actually reach for, and
what would notice `[latitude, longitude]` -- the single most common
way to get GeoJSON wrong, which renders perfectly and puts everybody
in the Gulf of Guinea.

Measured while this was written, with the real thing: `geopandas`
read the outings file as 19 features of `LineString` and `Point`, and
the anchors as 2 points. `geopandas` is not a dev dependency here
because it pulls GDAL and this suite runs on two platforms; `shapely`
is the part that does the parsing, and it is.
"""

import json
from datetime import UTC, datetime, timedelta

import pandas
import pytest
from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.time_range import TimeRange
from kiseki.interfaces import interchange
from shapely.geometry import shape

BASE = datetime(2025, 5, 3, 9, 0, tzinfo=UTC)

# Deliberately precise, and deliberately not round: a doorstep, so
# that blurring has something to remove and rounding cannot be
# mistaken for the value having been round already.
DOORSTEP = GeoPoint(35.0094123, 135.6669456)
ELSEWHERE = GeoPoint(34.6937111, 135.5023222)


def a_stop(place: GeoPoint, at: int, photographs: int = 3) -> Stop:
    return Stop(
        tuple(PhotoId(f"sha256:{at:02d}{index:02d}") for index in range(photographs)),
        TimeRange(BASE + timedelta(hours=at), BASE + timedelta(hours=at, minutes=20)),
        place,
    )


@pytest.fixture
def stops() -> tuple[Stop, ...]:
    return (a_stop(DOORSTEP, 1), a_stop(ELSEWHERE, 5))


@pytest.fixture
def outings(stops: tuple[Stop, ...]) -> tuple[Outing, ...]:
    return (Outing.of(stops), Outing.of([a_stop(DOORSTEP, 30)]))


@pytest.fixture
def anchors() -> tuple[Anchor, ...]:
    return (
        Anchor(
            area=GeoArea(DOORSTEP, Distance(120)),
            period=TimeRange(BASE, BASE + timedelta(days=90)),
            visit_days=40,
            night_days=38,
            weekday_days=30,
            daytime_days=12,
            photograph_count=210,
            confidence=Confidence(0.94, 40),
        ),
    )


class TestShapelyReadsTheGeometry:
    """Every geometry, parsed by a library that did not write it."""

    def test_stops_are_points(self, stops: tuple[Stop, ...]) -> None:
        document = interchange.stops_geojson(stops)
        for feature in document["features"]:
            assert shape(feature["geometry"]).geom_type == "Point"

    def test_an_outing_of_several_stops_is_a_line(self, outings: tuple[Outing, ...]) -> None:
        document = interchange.outings_geojson(outings)
        kinds = [shape(feature["geometry"]).geom_type for feature in document["features"]]
        assert "LineString" in kinds

    def test_an_outing_of_one_stop_is_a_point(self, outings: tuple[Outing, ...]) -> None:
        """RFC 7946 requires two positions for a LineString, and a
        one-stop outing is a real thing rather than an error."""
        document = interchange.outings_geojson(outings)
        kinds = [shape(feature["geometry"]).geom_type for feature in document["features"]]
        assert "Point" in kinds

    def test_anchors_are_points(self, anchors: tuple[Anchor, ...]) -> None:
        document = interchange.anchors_geojson(anchors)
        for feature in document["features"]:
            assert shape(feature["geometry"]).geom_type == "Point"

    def test_the_document_survives_a_round_trip_through_json(self, stops: tuple[Stop, ...]) -> None:
        """What lands in the file, not what was built in memory."""
        text = interchange.as_json(interchange.stops_geojson(stops))
        for feature in json.loads(text)["features"]:
            assert shape(feature["geometry"]).is_valid


class TestLongitudeComesFirst:
    """RFC 7946 section 3.1.1. Getting this wrong renders perfectly and
    puts a Kyoto library in the sea off West Africa, so it is checked
    by where shapely thinks the point is rather than by reading the
    list."""

    def test_shapely_places_the_point_where_it_belongs(self, stops: tuple[Stop, ...]) -> None:
        point = shape(interchange.stops_geojson(stops, precise=True)["features"][0]["geometry"])
        assert point.x == pytest.approx(DOORSTEP.longitude)
        assert point.y == pytest.approx(DOORSTEP.latitude)

    def test_the_latitude_is_in_range_for_a_latitude(self, stops: tuple[Stop, ...]) -> None:
        """Reversed coordinates for this library would put y at 135,
        which is not a latitude at all."""
        for position in interchange.every_position(interchange.stops_geojson(stops)):
            assert -90 <= position[1] <= 90


class TestCoordinatesAreBlurredUnlessAskedTwice:
    """The one part of this that is not a formatting decision."""

    def test_the_default_is_blurred(self, stops: tuple[Stop, ...]) -> None:
        document = interchange.stops_geojson(stops)
        assert document[interchange.PRECISION_KEY] == interchange.BLURRED

    def test_a_doorstep_does_not_survive_the_default(self, stops: tuple[Stop, ...]) -> None:
        """The whole point: the precise value must be absent, not
        merely absent from the top of the file."""
        text = interchange.as_json(interchange.stops_geojson(stops))
        assert str(DOORSTEP.latitude) not in text
        assert str(DOORSTEP.longitude) not in text

    def test_blurring_moves_the_point_by_about_a_kilometre_at_most(
        self, stops: tuple[Stop, ...]
    ) -> None:
        """Blurred has to mean something and also not too much. Two
        decimal places is roughly a kilometre; a reader who cannot
        find their own town has been given nothing."""
        blurred = shape(interchange.stops_geojson(stops)["features"][0]["geometry"])
        moved = DOORSTEP.distance_to(GeoPoint(blurred.y, blurred.x))
        assert 0 < moved.meters < 1600, f"blurring moved the point {moved.meters:.0f} m"

    def test_precise_is_precise(self, stops: tuple[Stop, ...]) -> None:
        text = interchange.as_json(interchange.stops_geojson(stops, precise=True))
        assert str(DOORSTEP.latitude) in text

    def test_precise_says_so_in_the_file(self, stops: tuple[Stop, ...]) -> None:
        document = interchange.stops_geojson(stops, precise=True)
        assert document[interchange.PRECISION_KEY] == interchange.PRECISE

    @pytest.mark.parametrize("subject", sorted(interchange.SUBJECTS))
    def test_every_subject_records_its_precision(
        self,
        subject: str,
        stops: tuple[Stop, ...],
        outings: tuple[Outing, ...],
        anchors: tuple[Anchor, ...],
    ) -> None:
        """A file that does not say gets assumed precise by whoever
        finds it, and they will be right half the time."""
        text = interchange.write(subject, "geojson", stops, outings, anchors)
        assert json.loads(text)[interchange.PRECISION_KEY] == interchange.BLURRED

    def test_the_csv_carries_it_on_every_row(self, stops: tuple[Stop, ...]) -> None:
        """A column and not a header comment: `read_csv` drops
        comments, and a reader who concatenates two files still needs
        to know which rows came from where."""
        frame = pandas.read_csv(_as_buffer(interchange.stops_csv(stops)))
        assert set(frame["precision"]) == {interchange.BLURRED}


def _as_buffer(text: str):  # type: ignore[no-untyped-def]
    import io

    return io.StringIO(text)


class TestPandasReadsTheCsv:
    def test_it_parses_with_the_types_a_reader_expects(self, stops: tuple[Stop, ...]) -> None:
        frame = pandas.read_csv(
            _as_buffer(interchange.stops_csv(stops)), parse_dates=["started_at", "ended_at"]
        )
        assert len(frame) == len(stops)
        assert str(frame["started_at"].dtype).startswith("datetime64")
        assert frame["latitude"].dtype.kind == "f"
        assert frame["photographs"].dtype.kind == "i"

    def test_the_columns_are_the_ones_promised(self, stops: tuple[Stop, ...]) -> None:
        frame = pandas.read_csv(_as_buffer(interchange.stops_csv(stops)))
        assert tuple(frame.columns) == interchange.STOP_COLUMNS

    def test_nothing_is_lost_when_a_value_needs_quoting(self) -> None:
        """Written with the `csv` module rather than by joining on
        commas, which is the mistake this format invites. There is no
        free text in these columns today, so this pins the machinery
        rather than a current value."""
        text = interchange.stops_csv((a_stop(DOORSTEP, 1),))
        assert len(pandas.read_csv(_as_buffer(text)).columns) == len(interchange.STOP_COLUMNS)


class TestAskingForSomethingThatIsNotAPoint:
    def test_csv_refuses_outings_and_says_why(
        self, stops: tuple[Stop, ...], outings: tuple[Outing, ...], anchors: tuple[Anchor, ...]
    ) -> None:
        """Better than a column called `coordinates` holding a string
        nobody can parse."""
        with pytest.raises(ValueError, match="not points"):
            interchange.write("outings", "csv", stops, outings, anchors)

    def test_csv_still_works_for_stops(
        self, stops: tuple[Stop, ...], outings: tuple[Outing, ...], anchors: tuple[Anchor, ...]
    ) -> None:
        assert interchange.write("stops", "csv", stops, outings, anchors).startswith("started_at,")


class TestNothingIsExportedThatWasNotAsked:
    def test_an_empty_library_is_an_empty_collection(self) -> None:
        """A valid GeoJSON document with no features, rather than an
        error. Every tool listed in the module docstring opens it."""
        document = interchange.stops_geojson(())
        assert document["type"] == "FeatureCollection"
        assert document["features"] == []
