"""Every detector, and what changing one costs.

Four algorithms in the domain and three more behind an extra. They are
not interchangeable and this file does not pretend they are: what it
pins is the contract they all keep, the ways they are allowed to
differ, and the one place two of them must agree exactly.

**The agreement is the interesting test.** `dbscan` in the domain and
`dbscan-indexed` in the adapters are the same published algorithm --
Ester et al., KDD 1996 -- written twice, once in plain Python and once
on scikit-learn's ball tree. Two implementations of one specification
that produce the same groups is the strongest evidence available that
either is right. Where they disagree, at least one is wrong, and no
amount of reading either would say which.
"""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.adapters.clustering import (
    ACCELERATED,
    available_detectors,
    detector_named,
    every_name,
    is_available,
)
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.services.detectors import DEFAULT_DETECTOR, DETECTORS
from kiseki.domain.services.stop_extraction import extract_stops
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.settings import StopSettings

BASE = datetime(2025, 5, 3, 9, 0, tzinfo=UTC)
HOME = GeoPoint(35.0094, 135.6669)
AWAY = GeoPoint(34.6937, 135.5023)

SETTINGS = StopSettings(min_photographs=4)


def north_of(origin: GeoPoint, metres: float) -> GeoPoint:
    return GeoPoint(origin.latitude + metres / 111_194.9, origin.longitude)


def a_library() -> list[PhotoObservation]:
    """Three visits to one place a week apart, then one visit to
    another. Deliberately unambiguous: every detector should find four
    stays, which is what makes the disagreements elsewhere meaningful."""
    observations = []
    index = 0
    for visit in range(3):
        for step in range(6):
            index += 1
            observations.append(
                PhotoObservation(
                    PhotoId(f"sha256:{index:04d}"),
                    BASE + timedelta(days=visit * 7, minutes=step * 5),
                    north_of(HOME, step * 20),
                )
            )
    for step in range(4):
        index += 1
        observations.append(
            PhotoObservation(
                PhotoId(f"sha256:{index:04d}"),
                BASE + timedelta(days=30, minutes=step * 5),
                AWAY,
            )
        )
    return observations


def a_diffuse_library(count: int) -> list[PhotoObservation]:
    """A deterministic spread with no obvious answer, for the
    properties that must hold whatever a detector decides."""
    observations = []
    for index in range(count):
        drift = ((index * 37) % 41 - 20) * 12.0
        observations.append(
            PhotoObservation(
                PhotoId(f"sha256:{index:04d}"),
                BASE + timedelta(minutes=index * 11),
                north_of(HOME, drift),
            )
        )
    return observations


class TestTheContractEveryDetectorKeeps:
    """Whatever it decides, a detector may not lose or duplicate a
    photograph. Every derivation above assumes this."""

    @pytest.mark.parametrize("name", sorted(available_detectors()))
    def test_every_photograph_appears_exactly_once(self, name: str) -> None:
        observations = a_library()
        result = detector_named(name)(observations, SETTINGS)
        seen = [photo for stop in result.stops for photo in stop.photo_ids]
        seen += list(result.in_transit) + list(result.unlocated)
        assert sorted(item.value for item in seen) == sorted(
            item.photo_id.value for item in observations
        ), f"{name} lost or duplicated a photograph"

    @pytest.mark.parametrize("name", sorted(available_detectors()))
    def test_nothing_at_all_yields_nothing(self, name: str) -> None:
        result = detector_named(name)([], SETTINGS)
        assert result.stops == () and result.in_transit == () and result.unlocated == ()

    @pytest.mark.parametrize("name", sorted(available_detectors()))
    def test_a_photograph_with_no_coordinates_is_set_aside(self, name: str) -> None:
        observations = [
            *a_library(),
            PhotoObservation(PhotoId("sha256:ffff"), BASE, None),
        ]
        result = detector_named(name)(observations, SETTINGS)
        assert result.unlocated == (PhotoId("sha256:ffff"),)

    @pytest.mark.parametrize("name", sorted(available_detectors()))
    def test_running_it_twice_gives_the_same_answer(self, name: str) -> None:
        """A derivation nobody can reproduce is a derivation nobody can
        check. Both DBSCANs and HDBSCAN have label orders that are not
        obliged to be stable, so this is pinned rather than assumed."""
        observations = a_diffuse_library(60)
        first = detector_named(name)(observations, SETTINGS)
        second = detector_named(name)(observations, SETTINGS)
        assert [stop.photo_ids for stop in first.stops] == [stop.photo_ids for stop in second.stops]

    @pytest.mark.parametrize("name", sorted(available_detectors()))
    def test_the_obvious_library_is_read_the_obvious_way(self, name: str) -> None:
        """Three visits to one place and one to another. A detector
        that cannot do this is not a detector."""
        assert len(detector_named(name)(a_library(), SETTINGS).stops) == 4


def test_the_extra_is_installed_in_this_repository() -> None:
    """Written instead of a `skipif`, and the difference matters.

    scikit-learn is a **dev dependency** here, so the extra is always
    present when these tests run. A `skipif` guarding that would never
    fire -- and the day somebody dropped the dev dependency it would
    fire silently, turning the comparison below into nothing while the
    run stayed green. An empty population spelled as *not applicable*
    is the failure this repository spent a day removing.

    So the condition is asserted rather than tested around. If the
    extra is genuinely absent, this fails and says which one thing to
    fix, instead of quietly measuring nothing.
    """
    assert is_available(), (
        "the clustering extra is not installed, so the accelerated detectors are "
        "untested here. Run `uv sync --all-packages`."
    )


class TestTheTwoImplementationsOfDbscan:
    """The same algorithm, written twice."""

    def groups(self, name: str, observations: list[PhotoObservation]) -> list[tuple[str, ...]]:
        result = detector_named(name)(observations, SETTINGS)
        return sorted(
            tuple(sorted(photo.value for photo in stop.photo_ids)) for stop in result.stops
        )

    @pytest.mark.parametrize("count", [30, 90, 200])
    def test_they_group_the_photographs_identically(self, count: int) -> None:
        observations = a_diffuse_library(count)
        assert self.groups("dbscan", observations) == self.groups("dbscan-indexed", observations)


class TestChoosingOne:
    def test_the_default_is_the_one_with_measured_thresholds(self) -> None:
        """ADR-0006's numbers came from a real photo library and belong
        to `sequential`. The others are correct implementations handed
        those numbers, which is a weaker claim."""
        assert DEFAULT_DETECTOR == "sequential"

    def test_extract_stops_without_a_detector_is_the_default(self) -> None:
        observations = a_diffuse_library(50)
        assert [stop.photo_ids for stop in extract_stops(observations, SETTINGS).stops] == [
            stop.photo_ids
            for stop in extract_stops(observations, SETTINGS, detector=DEFAULT_DETECTOR).stops
        ]

    def test_a_name_that_does_not_exist_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not a stop detector"):
            extract_stops(a_library(), SETTINGS, detector="k-means")

    def test_the_refusal_lists_the_alternatives(self) -> None:
        """A reader who mistyped needs the list, not the word no."""
        with pytest.raises(ValueError) as raised:
            detector_named("k-means")
        for name in every_name():
            assert name in str(raised.value)

    def test_a_detector_that_needs_the_extra_says_so(self) -> None:
        """When the extra is missing the message must name it, rather
        than reporting that the algorithm does not exist -- those are
        different problems with different fixes."""
        from kiseki.adapters.clustering import missing_extra

        message = missing_extra("hdbscan")
        assert "clustering" in message and "hdbscan" in message

    def test_every_accelerated_name_is_absent_from_the_domain(self) -> None:
        """The domain may not know this layer exists, so a name that
        needs a library must not appear in the domain's registry."""
        assert not set(ACCELERATED) & set(DETECTORS)

    def test_the_names_are_the_two_registries_and_nothing_else(self) -> None:
        assert set(every_name()) == set(DETECTORS) | set(ACCELERATED)
