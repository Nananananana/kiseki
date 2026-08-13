"""Specification for the pipeline use cases.

Every one of these runs on fakes. No database, no filesystem, no model. That the
whole sequence can be exercised this way is the point of the port design; see
ADR-0004.
"""

from datetime import datetime, timedelta, timezone

import pytest

from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint

JST = timezone(timedelta(hours=9))


@pytest.fixture
def pipeline() -> Pipeline:
    return Pipeline(
        InMemoryPhotoRepository(), InMemoryOutingRepository(), InMemoryAnchorRepository()
    )


def observation(
    name: str, day: int, hour: int, minute: int, latitude: float
) -> PhotoObservation:
    return PhotoObservation(
        PhotoId(f"{name}_{day}_{hour}_{minute}"),
        datetime(2026, 5, day, hour, minute, tzinfo=JST),
        GeoPoint(latitude, 135.0),
    )


def a_visit(name: str, day: int, hour: int, latitude: float) -> list[PhotoObservation]:
    return [observation(name, day, hour, index * 10, latitude) for index in range(6)]


class TestEmptyLibrary:
    def test_rebuilding_nothing_produces_nothing(self, pipeline: Pipeline) -> None:
        result = pipeline.rebuild()
        assert result.outings == 0
        assert result.stops == 0

    def test_reporting_on_nothing_does_not_fail(self, pipeline: Pipeline) -> None:
        """An empty library is a state to report, not an error."""
        report = pipeline.report()
        assert report.photographs == 0
        assert report.outings == ()
        assert report.habits is None


class TestIngest:
    def test_reports_how_many_were_taken_in(self, pipeline: Pipeline) -> None:
        assert pipeline.ingest(a_visit("a", 3, 9, 35.0)) == 6

    def test_ingesting_the_same_photographs_twice_stores_them_once(
        self, pipeline: Pipeline
    ) -> None:
        pipeline.ingest(a_visit("a", 3, 9, 35.0))
        pipeline.ingest(a_visit("a", 3, 9, 35.0))
        assert pipeline.report().photographs == 6


class TestRebuild:
    def test_finds_a_stop_and_an_outing(self, pipeline: Pipeline) -> None:
        pipeline.ingest(a_visit("a", 3, 9, 35.0))
        result = pipeline.rebuild()
        assert result.stops == 1
        assert result.outings == 1

    def test_stores_what_it_built(self, pipeline: Pipeline) -> None:
        pipeline.ingest(a_visit("a", 3, 9, 35.0))
        pipeline.rebuild()
        assert len(pipeline.report().outings) == 1

    def test_running_it_twice_changes_nothing(self, pipeline: Pipeline) -> None:
        """Rebuilding is the normal way to bring things up to date."""
        pipeline.ingest(a_visit("a", 3, 9, 35.0))
        assert pipeline.rebuild() == pipeline.rebuild()

    def test_new_photographs_produce_new_outings(self, pipeline: Pipeline) -> None:
        pipeline.ingest(a_visit("a", 3, 9, 35.0))
        pipeline.rebuild()
        pipeline.ingest(a_visit("b", 4, 9, 36.0))
        assert pipeline.rebuild().outings == 2

    def test_a_window_limits_what_is_considered(self, pipeline: Pipeline) -> None:
        pipeline.ingest(a_visit("a", 3, 9, 35.0))
        pipeline.ingest(a_visit("b", 4, 9, 36.0))
        result = pipeline.rebuild(since=datetime(2026, 5, 4, tzinfo=JST))
        assert result.photographs == 6
        assert result.outings == 1


class TestAnchors:
    def test_a_place_returned_to_becomes_an_anchor(self, pipeline: Pipeline) -> None:
        for day in range(1, 16):
            pipeline.ingest(a_visit("home", day, 21, 34.78))
        assert pipeline.rebuild().anchors == 1

    def test_the_anchor_carries_what_was_observed(self, pipeline: Pipeline) -> None:
        for day in range(1, 16):
            pipeline.ingest(a_visit("home", day, 21, 34.78))
        pipeline.rebuild()

        anchor = pipeline.report().anchors[0]
        assert anchor.visit_days == 15
        assert anchor.night_share == 1.0

    def test_one_visit_is_not_an_anchor(self, pipeline: Pipeline) -> None:
        pipeline.ingest(a_visit("away", 3, 12, 43.06))
        assert pipeline.rebuild().anchors == 0


class TestReport:
    def test_measures_what_was_built(self, pipeline: Pipeline) -> None:
        pipeline.ingest(a_visit("a", 3, 9, 35.0))
        pipeline.ingest(a_visit("b", 4, 9, 36.0))
        pipeline.rebuild()

        report = pipeline.report()
        assert report.habits is not None
        assert report.habits.outing_count == 2
        assert len(report.places.places) == 2

    def test_reads_from_storage_rather_than_recomputing(self, pipeline: Pipeline) -> None:
        """A report is cheap; rebuilding is not."""
        pipeline.ingest(a_visit("a", 3, 9, 35.0))
        assert pipeline.report().outings == ()

        pipeline.rebuild()
        assert len(pipeline.report().outings) == 1
