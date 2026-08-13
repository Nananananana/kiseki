"""Contract suites every repository implementation must satisfy.

Applied to both the fake used in tests and the SQLite implementation. A fake
that drifts from the real thing is worse than no fake at all, and running one
suite against both is what stops that happening.
"""

from datetime import timedelta

import pytest

from conftest import anchor, at, observation, outing, photo_id, stop
from kiseki.ports.repositories import (
    AnchorRepository,
    OutingRepository,
    PhotoRepository,
)


class PhotoRepositoryContract:
    @pytest.fixture
    def photos(self) -> PhotoRepository:
        raise NotImplementedError("override the 'photos' fixture")

    def test_starts_empty(self, photos: PhotoRepository) -> None:
        assert photos.count() == 0
        assert photos.all() == ()

    def test_reports_how_many_were_saved(self, photos: PhotoRepository) -> None:
        assert photos.save_all([observation(0, 9), observation(1, 10)]) == 2

    def test_saving_nothing_is_allowed(self, photos: PhotoRepository) -> None:
        assert photos.save_all([]) == 0

    def test_returns_what_was_saved(self, photos: PhotoRepository) -> None:
        photos.save_all([observation(0, 9), observation(1, 10)])
        assert photos.count() == 2

    def test_returns_them_in_time_order(self, photos: PhotoRepository) -> None:
        photos.save_all([observation(1, 14), observation(0, 9)])
        assert [item.captured_at for item in photos.all()] == [at(9), at(14)]

    def test_preserves_the_utc_offset(self, photos: PhotoRepository) -> None:
        """A stored timestamp that loses its offset cannot be ordered later."""
        photos.save_all([observation(0, 9)])
        assert photos.all()[0].captured_at.utcoffset() == timedelta(hours=9)

    def test_preserves_coordinates(self, photos: PhotoRepository) -> None:
        photos.save_all([observation(1, 9)])
        stored = photos.all()[0].location
        assert stored is not None
        assert stored.latitude == pytest.approx(35.01)

    def test_preserves_the_absence_of_coordinates(self, photos: PhotoRepository) -> None:
        photos.save_all([observation(0, 9, located=False)])
        assert photos.all()[0].location is None

    def test_saving_the_same_photograph_twice_stores_it_once(
        self, photos: PhotoRepository
    ) -> None:
        """Ingestion runs overlap. Re-importing must not duplicate."""
        photos.save_all([observation(0, 9)])
        photos.save_all([observation(0, 9)])
        assert photos.count() == 1

    def test_selects_a_window(self, photos: PhotoRepository) -> None:
        photos.save_all([observation(index, 9 + index) for index in range(6)])
        assert len(photos.between(at(10), at(12))) == 3

    def test_a_window_with_nothing_in_it_is_empty(self, photos: PhotoRepository) -> None:
        photos.save_all([observation(0, 9)])
        assert photos.between(at(20), at(22)) == ()


class OutingRepositoryContract:
    @pytest.fixture
    def outings(self) -> OutingRepository:
        raise NotImplementedError("override the 'outings' fixture")

    def test_starts_empty(self, outings: OutingRepository) -> None:
        assert outings.all() == ()

    def test_reports_how_many_were_saved(self, outings: OutingRepository) -> None:
        assert outings.replace_all([outing(stop("a", 9, 11, 35.0, 135.0))]) == 1

    def test_returns_what_was_saved(self, outings: OutingRepository) -> None:
        first = outing(stop("a", 9, 11, 35.0, 135.0), stop("b", 12, 13, 35.01, 135.01))
        second = outing(stop("c", 15, 16, 35.02, 135.02))
        outings.replace_all([first, second])

        stored = {item.id for item in outings.all()}
        assert stored == {first.id, second.id}

    def test_preserves_the_order_of_stops(self, outings: OutingRepository) -> None:
        subject = outing(stop("a", 9, 11, 35.0, 135.0), stop("b", 12, 13, 35.01, 135.01))
        outings.replace_all([subject])

        stored = outings.all()[0]
        assert [item.time_range.start for item in stored.stops] == [at(9), at(12)]

    def test_preserves_the_photographs_of_each_stop(self, outings: OutingRepository) -> None:
        subject = outing(stop("a", 9, 11, 35.0, 135.0))
        outings.replace_all([subject])
        assert outings.all()[0].stops[0].photo_ids == subject.stops[0].photo_ids

    def test_preserves_the_centroid(self, outings: OutingRepository) -> None:
        subject = outing(stop("a", 9, 11, 35.0, 135.0))
        outings.replace_all([subject])
        assert outings.all()[0].stops[0].centroid == subject.stops[0].centroid

    def test_replacing_discards_what_was_there(self, outings: OutingRepository) -> None:
        """Outings are recomputed wholesale, never edited in place."""
        outings.replace_all([outing(stop("a", 9, 11, 35.0, 135.0))])
        outings.replace_all([outing(stop("b", 12, 13, 35.01, 135.01))])
        assert len(outings.all()) == 1

    def test_replacing_with_nothing_empties_it(self, outings: OutingRepository) -> None:
        outings.replace_all([outing(stop("a", 9, 11, 35.0, 135.0))])
        outings.replace_all([])
        assert outings.all() == ()


class AnchorRepositoryContract:
    @pytest.fixture
    def anchors(self) -> AnchorRepository:
        raise NotImplementedError("override the 'anchors' fixture")

    def test_starts_empty(self, anchors: AnchorRepository) -> None:
        assert anchors.all() == ()

    def test_reports_how_many_were_saved(self, anchors: AnchorRepository) -> None:
        assert anchors.replace_all([anchor()]) == 1

    def test_returns_them_most_visited_first(self, anchors: AnchorRepository) -> None:
        anchors.replace_all([anchor(visits=12), anchor(visits=52)])
        assert [item.visit_days for item in anchors.all()] == [52, 12]

    def test_preserves_the_observed_shares(self, anchors: AnchorRepository) -> None:
        """The shares are the whole point of an anchor; losing them loses it."""
        anchors.replace_all([anchor(visits=52, nights=3)])
        stored = anchors.all()[0]
        assert stored.night_days == 3
        assert stored.night_share == pytest.approx(3 / 52)

    def test_preserves_the_area(self, anchors: AnchorRepository) -> None:
        subject = anchor()
        anchors.replace_all([subject])
        assert anchors.all()[0].area == subject.area

    def test_preserves_the_confidence(self, anchors: AnchorRepository) -> None:
        anchors.replace_all([anchor(visits=52)])
        assert anchors.all()[0].confidence.sample_size == 52

    def test_replacing_discards_what_was_there(self, anchors: AnchorRepository) -> None:
        anchors.replace_all([anchor(visits=52), anchor(visits=12)])
        anchors.replace_all([anchor(visits=7)])
        assert [item.visit_days for item in anchors.all()] == [7]


__all__ = [
    "AnchorRepositoryContract",
    "OutingRepositoryContract",
    "PhotoRepositoryContract",
    "anchor",
    "at",
    "observation",
    "outing",
    "photo_id",
    "stop",
]
