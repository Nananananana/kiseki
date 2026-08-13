"""Interests are read from the return pattern, and only from it.

Going back is the clearest statement of having liked somewhere, so a
place visited on more than one day becomes an interest. A place seen
once does not: single photographs are a different source of evidence
and arrive with captioning (FR-507). See ADR-0017.
"""

from datetime import date, datetime, timezone

import pytest

from kiseki.domain.analytics.analytics import PlacePreference, PlaceVisits
from kiseki.domain.interests import EvidenceKind
from kiseki.domain.services.interest_derivation import derive_interests
from kiseki.domain.shared.geo import GeoPoint

GENERATED = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)


def _place(
    visit_days: int = 3,
    first: date = date(2026, 1, 1),
    last: date = date(2026, 3, 2),
    photographs: int = 30,
    latitude: float = 35.65810,
    longitude: float = 139.70170,
) -> PlaceVisits:
    return PlaceVisits(
        centre=GeoPoint(latitude, longitude),
        visit_days=visit_days,
        first_visit=first,
        last_visit=last,
        photograph_count=photographs,
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


class TestWhatBecomesAnInterest:
    def test_an_empty_preference_yields_an_empty_profile(self) -> None:
        profile = derive_interests(_preference(), GENERATED)
        assert profile.interests == ()
        assert profile.generated_at == GENERATED

    def test_a_place_seen_once_is_not_an_interest(self) -> None:
        once = _place(visit_days=1, first=date(2026, 2, 1), last=date(2026, 2, 1))
        profile = derive_interests(_preference(once), GENERATED)
        assert profile.interests == ()

    def test_a_place_returned_to_becomes_an_interest(self) -> None:
        profile = derive_interests(_preference(_place()), GENERATED)
        assert len(profile.interests) == 1

    def test_interests_keep_the_given_ranking(self) -> None:
        # summarise_places already ranks by visit_days; derivation
        # must not reorder what the measures decided.
        often = _place(visit_days=5, latitude=35.71480, longitude=139.79670)
        rarely = _place(visit_days=2, latitude=35.63290, longitude=139.88040)
        profile = derive_interests(_preference(often, rarely), GENERATED)
        assert [i.topic for i in profile.interests] == [
            "place:35.71480,139.79670",
            "place:35.63290,139.88040",
        ]


class TestTheTopic:
    def test_names_the_place_without_labelling_it(self) -> None:
        profile = derive_interests(_preference(_place()), GENERATED)
        assert profile.interests[0].topic == "place:35.65810,139.70170"


class TestTheScore:
    def test_saturates_with_visit_days(self) -> None:
        two = derive_interests(_preference(_place(visit_days=2)), GENERATED)
        nine = derive_interests(_preference(_place(visit_days=9)), GENERATED)
        assert two.interests[0].score == pytest.approx(2 / 3)
        assert nine.interests[0].score == pytest.approx(0.9)

    def test_never_reaches_one(self) -> None:
        many = derive_interests(_preference(_place(visit_days=500)), GENERATED)
        assert many.interests[0].score < 1.0


class TestTheConfidence:
    def test_combines_visits_and_span(self) -> None:
        # 3 visit days over 60 days: (3 / 6) * (60 / 90) = 1 / 3.
        place = _place(visit_days=3, first=date(2026, 1, 1), last=date(2026, 3, 2))
        profile = derive_interests(_preference(place), GENERATED)
        assert profile.interests[0].confidence == pytest.approx(1 / 3)

    def test_a_long_habit_outweighs_a_recent_burst(self) -> None:
        # The same reading as ADR-0016: twelve visits over two years
        # deserve more trust than two visits last week.
        habit = _place(
            visit_days=12,
            first=date(2024, 6, 1),
            last=date(2026, 6, 1),
            latitude=35.71480,
            longitude=139.79670,
        )
        burst = _place(
            visit_days=2,
            first=date(2026, 5, 25),
            last=date(2026, 6, 1),
            latitude=35.63290,
            longitude=139.88040,
        )
        profile = derive_interests(_preference(habit, burst), GENERATED)
        by_topic = {i.topic: i for i in profile.interests}
        assert (
            by_topic["place:35.71480,139.79670"].confidence
            > by_topic["place:35.63290,139.88040"].confidence
        )


class TestTheEvidence:
    def test_points_at_the_first_and_last_visit(self) -> None:
        place = _place(first=date(2026, 1, 1), last=date(2026, 3, 2))
        interest = derive_interests(_preference(place), GENERATED).interests[0]
        assert len(interest.evidence) == 2
        assert all(e.kind is EvidenceKind.VISIT for e in interest.evidence)
        assert all(e.reference == interest.topic for e in interest.evidence)
        assert interest.evidence[0].observed_at == datetime(2026, 1, 1)
        assert interest.evidence[1].observed_at == datetime(2026, 3, 2)

    def test_first_and_last_seen_match_the_visits(self) -> None:
        place = _place(first=date(2026, 1, 1), last=date(2026, 3, 2))
        interest = derive_interests(_preference(place), GENERATED).interests[0]
        assert interest.first_seen == datetime(2026, 1, 1)
        assert interest.last_seen == datetime(2026, 3, 2)
