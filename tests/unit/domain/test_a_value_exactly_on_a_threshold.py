"""What happens exactly on the line, for every line the algorithm draws.

Found by mutation testing, not by reading (#376). `cosmic-ray` over
`stop_extraction.py` reported **17 survivors of 132**, and nearly all
of them were one shape:

    <=  becomes  <        <=  becomes  ==
    >=  becomes  >        >=  becomes  ==

Those are the comparisons the algorithm is made of, and **no test put
a value on any of them.** Changing `>=` to `>` on `min_photographs` --
so that a group of exactly five photographs stops being a stay -- left
all 1765 tests green.

That is not a hypothetical input. `DEFAULT_MIN_PHOTOGRAPHS = 5`, and a
real library lands on exactly five constantly. A threshold is a
decision about the *boundary*; a test that stays well clear of it has
tested everything except the decision.

**The boundary cannot be reached by construction, and that is the
first thing this file had to learn.** Placing a photograph "100 metres
north" of another, through degrees of latitude, measures back as

    100.00016208793998 m

-- 0.16 mm past the line, so `<= Distance(100)` is False and a test
named *exactly at the radius* was really testing *just outside it*.
The two distance thresholds are therefore taken **from the
measurement** rather than from the construction: place the point,
measure it, and make that measurement the threshold. Then the
comparison really is between two equal floats, which is the state the
surviving mutants lived in.

The counted thresholds -- photographs, minutes -- have no such
problem, and are written the obvious way.

Each test pins the value itself and one step either side. One step
either side is not decoration: a test only on the value cannot tell
`>=` from `==`.
"""

from datetime import UTC, datetime, timedelta

from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.services.stop_extraction import extract_stops
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.domain.shared.settings import StopSettings
from kiseki.domain.shared.speed import Speed

BASE = datetime(2025, 5, 3, 9, 0, tzinfo=UTC)
PARK = GeoPoint(35.0094, 135.6669)

DEGREES_PER_METRE = 1 / 111_194.9
"""Near enough to place a point; not near enough to land on a
threshold. See the note above."""


def north_of(origin: GeoPoint, metres: float) -> GeoPoint:
    return GeoPoint(origin.latitude + metres * DEGREES_PER_METRE, origin.longitude)


def at(minutes: float, place: GeoPoint, name: str) -> PhotoObservation:
    return PhotoObservation(PhotoId(name), BASE + timedelta(minutes=minutes), place)


def a_stay_of(count: int) -> StopSettings:
    """Only the named threshold decides. `min_duration` is put out of
    reach so a lone photograph -- which spans no time at all -- is not
    counted as a stay, which would make a split read as two stops
    rather than none."""
    return StopSettings(min_photographs=count, min_duration=timedelta(days=365))


class TestExactlyAtTheStayRadius:
    """`_continues`: `centroid.distance_to(candidate) <= stay_radius`.

    While the group holds one photograph its centroid is that
    photograph, so the measured distance between the two is the
    distance the rule compares.
    """

    def pair(self, metres: float) -> tuple[list[PhotoObservation], Distance]:
        second = north_of(PARK, metres)
        return (
            [at(0, PARK, "sha256:a"), at(60, second, "sha256:b")],
            PARK.distance_to(second),
        )

    def settings(self, radius: Distance) -> StopSettings:
        return StopSettings(
            stay_radius=radius,
            drift_speed=Speed.from_kilometers_per_hour(0.001),
            min_photographs=2,
            min_duration=timedelta(days=365),
        )

    def test_exactly_at_the_radius_is_inside(self) -> None:
        """The radius **is** the measured distance, so this is the
        equality case and not a near miss."""
        photographs, measured = self.pair(100)
        assert len(extract_stops(photographs, self.settings(measured)).stops) == 1, (
            "a photograph exactly at the radius left the stay"
        )

    def test_a_hair_inside_is_inside(self) -> None:
        photographs, measured = self.pair(100)
        wider = Distance(measured.meters + 0.001)
        assert len(extract_stops(photographs, self.settings(wider)).stops) == 1

    def test_a_hair_outside_is_outside(self) -> None:
        """Without this, nothing above separates `<=` from `<`."""
        photographs, measured = self.pair(100)
        narrower = Distance(measured.meters - 0.001)
        assert len(extract_stops(photographs, self.settings(narrower)).stops) == 0


class TestExactlyAtTheDriftSpeed:
    """`_continues`: `Speed.between(travelled, gap) <= drift_speed`.

    Reached only when the candidate is **outside** the radius, so the
    radius here is a metre.
    """

    def pair(self, metres: float) -> tuple[list[PhotoObservation], Speed]:
        second = north_of(PARK, metres)
        photographs = [at(0, PARK, "sha256:a"), at(1, second, "sha256:b")]
        return photographs, Speed.between(PARK.distance_to(second), timedelta(minutes=1))

    def settings(self, drift: Speed) -> StopSettings:
        return StopSettings(
            stay_radius=Distance(1),
            drift_speed=drift,
            min_photographs=2,
            min_duration=timedelta(days=365),
        )

    def test_exactly_at_the_drift_speed_continues_the_stay(self) -> None:
        photographs, measured = self.pair(60)
        assert len(extract_stops(photographs, self.settings(measured)).stops) == 1

    def test_a_hair_slower_continues_it(self) -> None:
        photographs, measured = self.pair(60)
        faster_allowance = Speed(measured.meters_per_second + 1e-9)
        assert len(extract_stops(photographs, self.settings(faster_allowance)).stops) == 1

    def test_a_hair_faster_ends_it(self) -> None:
        photographs, measured = self.pair(60)
        tighter = Speed(measured.meters_per_second - 1e-9)
        assert len(extract_stops(photographs, self.settings(tighter)).stops) == 0


class TestExactlyAtMinPhotographs:
    """`_is_a_stay`: `len(group) >= min_photographs`.

    The one a real library meets most often: the default is five.
    """

    def close_together(self, count: int) -> list[PhotoObservation]:
        return [at(index, north_of(PARK, index), f"sha256:p{index}") for index in range(count)]

    def test_exactly_min_photographs_is_a_stay(self) -> None:
        assert len(extract_stops(self.close_together(5), a_stay_of(5)).stops) == 1

    def test_one_more_is_a_stay(self) -> None:
        assert len(extract_stops(self.close_together(6), a_stay_of(5)).stops) == 1

    def test_one_fewer_is_not(self) -> None:
        result = extract_stops(self.close_together(4), a_stay_of(5))
        assert result.stops == ()
        assert len(result.in_transit) == 4, "the photographs were dropped rather than set aside"


class TestExactlyAtMinDuration:
    """`_is_a_stay`: `span.duration >= min_duration`.

    `min_photographs` is put out of reach so the duration decides.
    """

    def settings(self) -> StopSettings:
        return StopSettings(min_duration=timedelta(minutes=10), min_photographs=1_000_000)

    def spanning(self, minutes: float) -> list[PhotoObservation]:
        return [at(0, PARK, "sha256:a"), at(minutes, north_of(PARK, 1), "sha256:b")]

    def test_exactly_min_duration_is_a_stay(self) -> None:
        assert len(extract_stops(self.spanning(10), self.settings()).stops) == 1

    def test_a_minute_longer_is_a_stay(self) -> None:
        assert len(extract_stops(self.spanning(11), self.settings()).stops) == 1

    def test_a_minute_shorter_is_not(self) -> None:
        assert extract_stops(self.spanning(9), self.settings()).stops == ()


class TestExactlyAtMaxGap:
    """`_continues`: `gap > max_gap` ends the stay.

    Written the other way round from the rest, so the boundary belongs
    to the *continuing* side: a silence of exactly `max_gap` does not
    end a stay.
    """

    def settings(self) -> StopSettings:
        return StopSettings(
            max_gap=timedelta(minutes=90),
            min_photographs=2,
            min_duration=timedelta(days=365),
        )

    def separated_by(self, minutes: float) -> list[PhotoObservation]:
        return [at(0, PARK, "sha256:a"), at(minutes, north_of(PARK, 1), "sha256:b")]

    def test_a_gap_of_exactly_max_gap_does_not_end_the_stay(self) -> None:
        assert len(extract_stops(self.separated_by(90), self.settings()).stops) == 1

    def test_a_minute_less_does_not_either(self) -> None:
        assert len(extract_stops(self.separated_by(89), self.settings()).stops) == 1

    def test_a_minute_more_does(self) -> None:
        assert len(extract_stops(self.separated_by(91), self.settings()).stops) == 0


class TestTwoPhotographsAtOneInstant:
    """`_continues`: `if gap.total_seconds() <= 0: return False`.

    The guard the mutation run pointed at, and the only one of the
    survivors that turned out to protect something. `Speed.between`
    refuses a zero duration -- *duration must be positive to derive a
    speed* -- so a candidate outside the stay radius whose timestamp
    equals the previous one would raise `ValueError` out of the middle
    of a build if this line were not here.

    Not a contrived input. A library merged from two devices carries
    identical timestamps often, and a camera writing whole seconds
    does it during a burst.

    Removing the guard makes both tests below raise rather than fail,
    which is how the crash would have reached a reader.
    """

    def settings(self) -> StopSettings:
        return StopSettings(
            stay_radius=Distance(10),
            min_photographs=2,
            min_duration=timedelta(days=365),
        )

    def at_one_instant(self, metres_apart: float) -> list[PhotoObservation]:
        return [
            at(0, PARK, "sha256:a"),
            at(0, north_of(PARK, metres_apart), "sha256:b"),
        ]

    def test_far_apart_at_one_instant_does_not_raise(self) -> None:
        """Outside the radius, so the speed rule is reached with a gap
        of zero -- the state the guard exists for."""
        result = extract_stops(self.at_one_instant(500), self.settings())
        assert result.stops == (), "two places at one instant cannot be one stay"
        assert len(result.in_transit) == 2

    def test_close_together_at_one_instant_is_one_stay(self) -> None:
        """Inside the radius the guard is never reached, and the two
        belong together."""
        assert len(extract_stops(self.at_one_instant(1), self.settings()).stops) == 1
