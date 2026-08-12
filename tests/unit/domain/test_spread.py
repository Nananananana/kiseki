"""Specification for Spread."""

import pytest

from kiseki.domain.analytics.analytics import Spread


class TestSpread:
    def test_summarises_an_odd_length_sequence(self) -> None:
        spread = Spread.of([1.0, 2.0, 3.0])
        assert spread.count == 3
        assert spread.minimum == 1.0
        assert spread.median == 2.0
        assert spread.mean == 2.0
        assert spread.maximum == 3.0

    def test_takes_the_midpoint_of_an_even_length_sequence(self) -> None:
        assert Spread.of([1.0, 2.0, 3.0, 4.0]).median == 2.5

    def test_a_single_value_is_every_statistic(self) -> None:
        spread = Spread.of([5.0])
        assert spread.minimum == spread.median == spread.mean == spread.maximum == 5.0

    def test_does_not_require_sorted_input(self) -> None:
        spread = Spread.of([3.0, 1.0, 2.0])
        assert spread.minimum == 1.0
        assert spread.maximum == 3.0

    def test_the_median_resists_an_outlier_the_mean_does_not(self) -> None:
        """Why both are reported: one long trip should not redefine a habit."""
        spread = Spread.of([2.0, 3.0, 4.0, 500.0])
        assert spread.median == 3.5
        assert spread.mean > 100

    def test_rejects_an_empty_sequence(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Spread.of([])
