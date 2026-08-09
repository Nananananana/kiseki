"""Specification for TimeRange."""

from datetime import datetime, timedelta, timezone

import pytest

from kiseki.domain.shared.time_range import TimeRange

JST = timezone(timedelta(hours=9))


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2025, 5, 3, hour, minute, tzinfo=JST)


class TestConstruction:
    def test_exposes_its_duration(self) -> None:
        assert TimeRange(at(9), at(11)).duration == timedelta(hours=2)

    def test_an_instant_is_allowed(self) -> None:
        assert TimeRange(at(9), at(9)).duration == timedelta(0)

    def test_rejects_a_naive_start(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            TimeRange(datetime(2025, 5, 3, 9), at(11))

    def test_rejects_a_naive_end(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            TimeRange(at(9), datetime(2025, 5, 3, 11))

    def test_rejects_an_end_before_the_start(self) -> None:
        with pytest.raises(ValueError, match="end before"):
            TimeRange(at(11), at(9))

    def test_compares_across_offsets(self) -> None:
        """The same instant expressed in two zones is the same instant."""
        utc = datetime(2025, 5, 3, 0, tzinfo=timezone.utc)
        assert TimeRange(utc, at(11)).duration == timedelta(hours=2)


class TestContains:
    def test_includes_a_moment_inside(self) -> None:
        assert TimeRange(at(9), at(11)).contains(at(10))

    def test_includes_both_boundaries(self) -> None:
        span = TimeRange(at(9), at(11))
        assert span.contains(at(9))
        assert span.contains(at(11))

    def test_excludes_a_moment_outside(self) -> None:
        assert not TimeRange(at(9), at(11)).contains(at(12))

    def test_rejects_a_naive_moment(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            TimeRange(at(9), at(11)).contains(datetime(2025, 5, 3, 10))


class TestOverlapAndGap:
    def test_detects_an_overlap(self) -> None:
        assert TimeRange(at(9), at(11)).overlaps(TimeRange(at(10), at(12)))

    def test_touching_ranges_overlap(self) -> None:
        assert TimeRange(at(9), at(10)).overlaps(TimeRange(at(10), at(11)))

    def test_disjoint_ranges_do_not_overlap(self) -> None:
        assert not TimeRange(at(9), at(10)).overlaps(TimeRange(at(11), at(12)))

    def test_gap_to_a_later_range(self) -> None:
        assert TimeRange(at(9), at(10)).gap_to(TimeRange(at(11), at(12))) == timedelta(hours=1)

    def test_gap_to_an_earlier_range_is_not_negative(self) -> None:
        assert TimeRange(at(11), at(12)).gap_to(TimeRange(at(9), at(10))) == timedelta(hours=1)

    def test_overlapping_ranges_have_no_gap(self) -> None:
        assert TimeRange(at(9), at(11)).gap_to(TimeRange(at(10), at(12))) == timedelta(0)


class TestSpanning:
    def test_spans_unordered_moments(self) -> None:
        assert TimeRange.spanning([at(11), at(9), at(10)]) == TimeRange(at(9), at(11))

    def test_spans_a_single_moment(self) -> None:
        assert TimeRange.spanning([at(9)]) == TimeRange(at(9), at(9))

    def test_rejects_an_empty_sequence(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            TimeRange.spanning([])
