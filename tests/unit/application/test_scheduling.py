"""`fan_out` runs several one-element calls at once and keeps each fate.

The loops that call a model send one request per call on purpose,
because a batch raises on its first failure and the loops want
per-item semantics (ADR-0015). This is the scheduler that lets them
keep that while running several at once, so what is specified here is
exactly what the loops rely on: order, isolation of failures, the
pause, and that anything unexpected still crashes.
"""

import threading
import time

import pytest
from kiseki.application.scheduling import Outcome, fan_out
from kiseki.ports.models import ModelRefusedError, ModelUnavailableError


def test_one_at_a_time_is_a_plain_loop() -> None:
    seen: list[int] = []

    def call(item: int) -> int:
        seen.append(item)
        return item * 10

    outcomes = fan_out([1, 2, 3], call, parallel=1)
    assert seen == [1, 2, 3]
    assert [one.completed for one in outcomes] == [10, 20, 30]


def test_outcomes_come_back_in_submission_order_however_they_finish() -> None:
    """The loops save in order so 'oldest first' survives the pool."""

    def call(item: int) -> int:
        time.sleep(0.05 if item == 1 else 0.0)
        return item

    outcomes = fan_out([1, 2, 3, 4], call, parallel=4)
    assert [one.completed for one in outcomes] == [1, 2, 3, 4]


def test_calls_actually_overlap_when_asked_to() -> None:
    """Not a timing test: a barrier that only opens when all four have
    arrived cannot open at all if they run one after another."""
    gate = threading.Barrier(4, timeout=2.0)

    def call(item: int) -> int:
        gate.wait()
        return item

    outcomes = fan_out([1, 2, 3, 4], call, parallel=4)
    assert [one.completed for one in outcomes] == [1, 2, 3, 4]


def test_a_refusal_is_that_item_s_alone() -> None:
    def call(item: int) -> int:
        if item == 2:
            raise ModelRefusedError("no")
        return item

    outcomes = fan_out([1, 2, 3], call, parallel=3)
    assert outcomes[0].completed == 1
    assert isinstance(outcomes[1].refused, ModelRefusedError)
    assert outcomes[2].completed == 3


def test_an_unavailable_model_is_reported_and_the_rest_of_the_window_still_lands() -> None:
    def call(item: int) -> int:
        if item == 1:
            raise ModelUnavailableError("down")
        return item

    outcomes = fan_out([1, 2, 3], call, parallel=3)
    assert isinstance(outcomes[0].unavailable, ModelUnavailableError)
    assert [one.completed for one in outcomes[1:]] == [2, 3]


def test_one_at_a_time_stops_submitting_after_an_unavailable_model() -> None:
    """What every loop did before this module existed."""
    seen: list[int] = []

    def call(item: int) -> int:
        seen.append(item)
        if item == 2:
            raise ModelUnavailableError("down")
        return item

    outcomes = fan_out([1, 2, 3], call, parallel=1)
    assert seen == [1, 2]
    assert len(outcomes) == 2


def test_anything_else_still_crashes() -> None:
    """A ValueError from a domain object is a defect to be seen, not a
    refusal to be recorded."""

    def call(item: int) -> int:
        raise ValueError("a bug")

    with pytest.raises(ValueError, match="a bug"):
        fan_out([1], call, parallel=1)
    with pytest.raises(ValueError, match="a bug"):
        fan_out([1, 2], call, parallel=2)


def test_zero_in_flight_is_refused() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        fan_out([1], lambda item: item, parallel=0)


def test_nothing_to_do_is_nothing() -> None:
    assert fan_out([], lambda item: item, parallel=4) == []


def test_an_outcome_is_exactly_one_thing() -> None:
    with pytest.raises(ValueError):
        Outcome(item=1)
    with pytest.raises(ValueError):
        Outcome(item=1, completed=1, refused=ModelRefusedError("no"))
