"""Specification for the Anchor aggregate."""

from datetime import datetime, timedelta, timezone

import pytest
from kiseki.domain.anchor.anchor import Anchor, AnchorKind
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))
AREA = GeoArea(GeoPoint(34.7810, 135.4700), Distance(500))
PERIOD = TimeRange(
    datetime(2026, 6, 1, tzinfo=JST),
    datetime(2026, 6, 30, tzinfo=JST),
)


def anchor(kind: AnchorKind = AnchorKind.PRIMARY, visits: int = 20, nights: int = 18) -> Anchor:
    return Anchor(kind, AREA, PERIOD, visits, nights, Confidence(0.9, visits))


class TestConstruction:
    def test_holds_where_and_when(self) -> None:
        subject = anchor()
        assert subject.area == AREA
        assert subject.period == PERIOD

    def test_rejects_an_anchor_with_no_visits(self) -> None:
        """An anchor is a place returned to. One visit is not returning."""
        with pytest.raises(ValueError, match="at least one visit"):
            anchor(visits=0)

    def test_rejects_a_negative_night_count(self) -> None:
        with pytest.raises(ValueError, match="night"):
            anchor(nights=-1)


class TestKind:
    def test_a_primary_anchor_is_residential(self) -> None:
        assert anchor(AnchorKind.PRIMARY).is_residential

    def test_a_secondary_anchor_is_residential(self) -> None:
        """A family home or a holiday place is somewhere you sleep."""
        assert anchor(AnchorKind.SECONDARY).is_residential

    def test_a_workplace_is_not_residential(self) -> None:
        assert not anchor(AnchorKind.WORKPLACE, nights=0).is_residential
