"""Places inside an anchor's area do not become interests.

ADR-0017 derives interests from the return pattern of outings because
anchors describe circumstances, not choices. Stops inside an anchor's
own area are the same circumstances seen through the outings, so the
derivation leaves them out.
"""

from datetime import UTC, date, datetime

from kiseki.domain.analytics.analytics import PlacePreference, PlaceVisits
from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.services.interest_derivation import derive_interests
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.time_range import TimeRange

GENERATED = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _place(latitude: float, longitude: float) -> PlaceVisits:
    return PlaceVisits(
        centre=GeoPoint(latitude, longitude),
        visit_days=3,
        first_visit=date(2026, 1, 1),
        last_visit=date(2026, 3, 2),
        photograph_count=30,
    )


def _preference(*places: PlaceVisits) -> PlacePreference:
    returned = sum(1 for place in places if place.was_returned_to)
    total = len(places)
    return PlacePreference(
        places=tuple(places),
        return_rate=returned / total if total else 0.0,
        one_time_rate=(total - returned) / total if total else 0.0,
        most_returned_to=tuple(p for p in places if p.was_returned_to),
    )


def _anchor(latitude: float, longitude: float, radius_m: float = 500) -> Anchor:
    return Anchor(
        area=GeoArea(GeoPoint(latitude, longitude), Distance(radius_m)),
        period=TimeRange(
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 6, 1, tzinfo=UTC),
        ),
        visit_days=50,
        night_days=45,
        weekday_days=40,
        daytime_days=48,
        photograph_count=400,
        confidence=Confidence(0.9, 50),
    )


class TestAnchoredExclusion:
    def test_a_place_inside_an_anchor_is_not_an_interest(self) -> None:
        profile = derive_interests(
            _preference(_place(35.0, 135.0)),
            GENERATED,
            anchors=(_anchor(35.0, 135.0),),
        )
        assert profile.interests == ()

    def test_a_place_beyond_the_anchor_radius_still_is(self) -> None:
        # 0.02 degrees of latitude is roughly 2.2 km, far outside 500 m.
        profile = derive_interests(
            _preference(_place(35.02, 135.0)),
            GENERATED,
            anchors=(_anchor(35.0, 135.0),),
        )
        assert len(profile.interests) == 1

    def test_without_anchors_nothing_changes(self) -> None:
        profile = derive_interests(_preference(_place(35.0, 135.0)), GENERATED)
        assert len(profile.interests) == 1

    def test_each_anchor_shields_its_own_surroundings(self) -> None:
        near_home = _place(35.0, 135.0)
        near_work = _place(35.1, 135.1)
        far_away = _place(43.0, 141.0)
        profile = derive_interests(
            _preference(near_home, near_work, far_away),
            GENERATED,
            anchors=(_anchor(35.0, 135.0), _anchor(35.1, 135.1)),
        )
        assert [interest.topic for interest in profile.interests] == ["place:43.00000,141.00000"]
