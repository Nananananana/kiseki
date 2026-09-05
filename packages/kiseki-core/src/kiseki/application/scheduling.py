"""Several one-element calls at once, with each keeping its own fate.

The three loops that call a model -- stays, lone photographs,
screenshots -- each send a batch of exactly one request. Deliberately:
a batch raises on its first failing request, and the loops want
per-item semantics (ADR-0015). A refusal is recorded against that
item and never asked again; an unavailable model pauses the run; and
nothing else is caught, so a bug is a crash and not a quiet gap.

Measured, one stay at a time on this machine: about six seconds a
caption, 4,950 photographs, hours. The model server answers several
requests concurrently and the loop never asked it to.

This module runs several of those one-element calls at once and hands
back one outcome per item, in submission order, so the loops can keep
every rule they had:

    parallel = 1     a plain loop. Identical to before, including
                     stopping at the first unavailable model
    parallel > 1     a thread pool of that size. Every item still gets
                     its own outcome; an unavailable model still pauses
                     the run, after the window it was in

Threads rather than asyncio because the transport is `urllib` and the
adapters are synchronous; a pool of blocking calls is the whole of
what is needed, and it changes no port.

**What is and is not caught.** `ModelRefusedError` and
`ModelUnavailableError` become outcomes. Anything else raised inside
a call propagates out of `fan_out` exactly as it would out of a loop,
because a `ValueError` from a domain object is a defect to be seen,
not a refusal to be recorded.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from kiseki.ports.models import ModelRefusedError, ModelUnavailableError


@dataclass(frozen=True)
class Outcome[W, T]:
    """What happened to one item: exactly one of the three is set."""

    item: W
    completed: T | None = None
    refused: ModelRefusedError | None = None
    unavailable: ModelUnavailableError | None = None

    def __post_init__(self) -> None:
        set_count = sum(
            1 for one in (self.completed, self.refused, self.unavailable) if one is not None
        )
        if set_count != 1:
            raise ValueError("an outcome is a completion, a refusal or an unavailability")


def _one[W, T](item: W, call: Callable[[W], T]) -> Outcome[W, T]:
    try:
        return Outcome(item, completed=call(item))
    except ModelRefusedError as error:
        return Outcome(item, refused=error)
    except ModelUnavailableError as error:
        return Outcome(item, unavailable=error)


def fan_out[W, T](
    items: Sequence[W],
    call: Callable[[W], T],
    parallel: int = 1,
) -> list[Outcome[W, T]]:
    """One outcome per item, in the order the items were given.

    With `parallel` of one this is a loop that stops submitting after
    the first unavailable model, which is what every loop did before
    this module existed. With more, the whole window is submitted and
    every item's fate is reported; the caller decides to pause after
    seeing an unavailability, and loses nothing that completed.
    """
    if parallel < 1:
        raise ValueError(f"parallel must be at least 1, not {parallel}")
    if not items:
        return []
    if parallel == 1:
        outcomes: list[Outcome[W, T]] = []
        for item in items:
            outcome = _one(item, call)
            outcomes.append(outcome)
            if outcome.unavailable is not None:
                break
        return outcomes
    with ThreadPoolExecutor(max_workers=min(parallel, len(items))) as pool:
        return list(pool.map(lambda item: _one(item, call), items))
