"""Specification for the Stop entity."""

from datetime import datetime, timedelta, timezone

import pytest

from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))
SPAN = TimeRange(
    datetime(2025, 5, 3, 9, 20, tzinfo=JST),
    datetime(2025, 5, 3, 11, 40, tzinfo=JST),
)
KYOTO = GeoPoint(35.0094, 135.6669)


class TestStop:
    def test_reports_how_many_photographs_it_holds(self) -> None:
        stop = Stop((PhotoId("a"), PhotoId("b")), SPAN, KYOTO)
        assert stop.photograph_count == 2

    def test_exposes_its_duration(self) -> None:
        assert Stop((PhotoId("a"),), SPAN, KYOTO).duration == timedelta(hours=2, minutes=20)

    def test_rejects_a_stop_with_no_photographs(self) -> None:
        """A stop is evidence of presence. Without a photograph there is none."""
        with pytest.raises(ValueError, match="at least one"):
            Stop((), SPAN, KYOTO)

    def test_rejects_duplicate_photographs(self) -> None:
        with pytest.raises(ValueError, match="duplicate"):
            Stop((PhotoId("a"), PhotoId("a")), SPAN, KYOTO)
