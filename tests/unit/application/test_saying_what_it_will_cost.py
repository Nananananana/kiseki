"""What the model work left to do will take, and when not to say.

Measured before this existed: building stops, outings and anchors for
a hundred thousand photographs takes **1.94 seconds**; captioning the
stays that finds takes **eight and a half hours** at 3.03 seconds a
call. The two ends of this library are four orders of magnitude apart,
and a reader deciding whether to start needs the second number.

The work was always resumable -- a second run costs nothing for what
is done. That was never the problem. The problem was that nobody was
told what the first run costs, so a reader with fifty thousand
photographs watched it caption for twenty minutes with no way to know
they were at five percent.

**The hard case is the stage that cannot be counted**, and it is the
reason this is a module rather than a multiplication. A total that
quietly drops a stage is confidently low: the reader plans an hour and
waits three, and the arithmetic was correct about the part it did.
"""

import pytest
from kiseki.application.estimating import UNKNOWN, Stage, estimate, in_words


def a_stage(name: str = "stay captions", outstanding: int = 100, rate: float | None = 3.0) -> Stage:
    return Stage(name, outstanding, rate, "a stay")


class TestOneStage:
    def test_the_estimate_is_the_count_times_the_rate(self) -> None:
        assert a_stage(outstanding=100, rate=3.0).seconds == pytest.approx(300.0)

    def test_a_stage_with_nothing_left_costs_nothing(self) -> None:
        assert a_stage(outstanding=0).seconds == 0.0

    def test_a_stage_with_no_rate_cannot_be_estimated(self) -> None:
        stage = a_stage(rate=None)
        assert not stage.estimable
        assert stage.seconds == 0.0

    def test_a_stage_that_could_not_be_counted_is_not_zero(self) -> None:
        """The distinction the whole module exists for. Zero means
        there is nothing to do; UNKNOWN means nobody knows."""
        stage = a_stage(outstanding=UNKNOWN)
        assert not stage.counted
        assert stage.outstanding != 0


class TestATotalThatDropsAStage:
    """A total missing a stage is worse than no total."""

    def test_it_is_reported_as_a_floor(self) -> None:
        report = estimate([a_stage(outstanding=100), a_stage("screens", UNKNOWN)])
        assert report.is_a_floor

    def test_the_missing_stage_is_named_rather_than_dropped(self) -> None:
        report = estimate([a_stage(outstanding=100), a_stage("screens", UNKNOWN)])
        assert [stage.name for stage in report.unestimable] == ["screens"]

    def test_the_total_still_covers_what_it_could(self) -> None:
        """A floor is useful; silence is not."""
        report = estimate([a_stage(outstanding=100, rate=3.0), a_stage("screens", UNKNOWN)])
        assert report.seconds == pytest.approx(300.0)

    def test_a_complete_estimate_is_not_a_floor(self) -> None:
        report = estimate([a_stage(outstanding=100), a_stage("screens", 5)])
        assert not report.is_a_floor
        assert report.unestimable == ()

    def test_an_unreachable_model_makes_every_stage_unestimable(self) -> None:
        """No rate measured: the counts are still true and are still
        worth printing, but nothing may be added up."""
        report = estimate([a_stage(rate=None), a_stage("screens", 5, None)])
        assert report.estimable == ()
        assert report.is_a_floor


class TestNothingToDo:
    def test_a_library_that_is_finished_says_so(self) -> None:
        report = estimate([a_stage(outstanding=0), a_stage("screens", 0)])
        assert report.nothing_to_do

    def test_an_uncounted_stage_does_not_make_it_finished(self) -> None:
        """`nothing_to_do` reads only the stages it could count, so
        this is the pairing that matters: finished-looking **and** a
        floor is not finished."""
        report = estimate([a_stage(outstanding=0), a_stage("screens", UNKNOWN)])
        assert report.nothing_to_do
        assert report.is_a_floor, (
            "a stage nobody counted must keep the caller from reporting completion"
        )

    def test_work_remaining_is_not_finished(self) -> None:
        assert not estimate([a_stage(outstanding=1)]).nothing_to_do


class TestSayingItInWords:
    """Deliberately coarse. An estimate from one timed call is not
    accurate to the minute, and `4h 17m 33s` would claim a precision
    the measurement does not have."""

    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (0, "under a minute"),
            (59, "under a minute"),
            (60, "about 1 minutes"),
            (600, "about 10 minutes"),
            (3599, "about 60 minutes"),
            (3600, "about 1.0 hours"),
            (15_390, "about 4.3 hours"),
            (36_000, "about 10 hours"),
            (30_600, "about 8.5 hours"),
        ],
    )
    def test_it_reads_the_way_a_person_would_say_it(self, seconds: float, expected: str) -> None:
        assert in_words(seconds) == expected

    def test_the_measured_library_reads_as_it_was_measured(self) -> None:
        """5,100 stays at 3.03 seconds is the 50,000-photograph
        library from the audit. If this stops saying 4.3 hours, either
        the arithmetic or the issue is wrong."""
        assert in_words(5_100 * 3.03) == "about 4.3 hours"
