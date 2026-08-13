"""Specification for the Anchor aggregate."""

from datetime import datetime, timedelta, timezone

import pytest
from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))
AREA = GeoArea(GeoPoint(34.7810, 135.4700), Distance(500))
PERIOD = TimeRange(datetime(2026, 6, 1, tzinfo=JST), datetime(2026, 6, 30, tzinfo=JST))


def anchor(
    visits: int = 20,
    nights: int = 18,
    weekdays: int = 14,
    daytime: int = 2,
    photographs: int = 100,
) -> Anchor:
    return Anchor(
        area=AREA,
        period=PERIOD,
        visit_days=visits,
        night_days=nights,
        weekday_days=weekdays,
        daytime_days=daytime,
        photograph_count=photographs,
        confidence=Confidence(0.9, visits),
    )


class TestConstruction:
    def test_holds_where_and_when(self) -> None:
        assert anchor().area == AREA
        assert anchor().period == PERIOD

    def test_rejects_an_anchor_with_no_visits(self) -> None:
        """An anchor is a place returned to. One visit is not returning."""
        with pytest.raises(ValueError, match="at least one visit"):
            anchor(visits=0)

    def test_rejects_a_negative_count(self) -> None:
        with pytest.raises(ValueError, match="night_days"):
            anchor(nights=-1)

    def test_a_count_cannot_exceed_the_visits_it_is_drawn_from(self) -> None:
        with pytest.raises(ValueError, match="cannot exceed"):
            anchor(visits=5, nights=6)


class TestShares:
    def test_reports_what_share_of_visits_included_a_night(self) -> None:
        assert anchor(visits=20, nights=18).night_share == 0.9

    def test_reports_what_share_fell_on_weekdays(self) -> None:
        assert anchor(visits=20, weekdays=14).weekday_share == 0.7

    def test_reports_what_share_fell_in_working_hours(self) -> None:
        assert anchor(visits=20, daytime=2).daytime_share == 0.1

    def test_reports_how_heavily_it_is_photographed(self) -> None:
        assert anchor(visits=20, photographs=100).photographs_per_visit == 5.0

    def test_the_shares_describe_a_place_without_naming_it(self) -> None:
        """A high night share and no daytime is recognisable without a label."""
        home_like = anchor(visits=20, nights=20, weekdays=14, daytime=0)
        assert home_like.night_share == 1.0
        assert home_like.daytime_share == 0.0
