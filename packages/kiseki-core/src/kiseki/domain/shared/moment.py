"""Comparing two moments that may not agree about time zones.

A photograph carries the offset its camera knew. A profile carries
whatever the clock said when it was derived. A command asks "how long
ago" with the clock it has now. All three are legitimate, and Python
refuses to subtract an aware moment from a naive one -- correctly,
because the answer would be a guess.

The library's answer is to compare in one shape at the moment of
comparison, and to store what it was given. Stored text keeps its
offset, so the API and the view still say "+09:00"; arithmetic drops
to naive local time, because every question this library asks about
time -- how many days since, how many months apart, which reading came
first -- is asked within one person's life and answered the same way in
any zone.

This helper existed six times under six names before it existed once.
Four derivations did not have it at all, and every history feature fell
over on a library whose timestamps carried offsets -- which the real one
happened not to. See ADR-0064.
"""

from __future__ import annotations

from datetime import datetime


def naive(moment: datetime) -> datetime:
    """The same moment, without a time zone, for arithmetic.

    Aware moments are converted rather than truncated: an offset that
    said midnight in Tokyo does not become midnight in London.
    """
    if moment.tzinfo is None:
        return moment
    return moment.astimezone().replace(tzinfo=None)


def days_between(earlier: datetime, later: datetime) -> int:
    """Whole days from one moment to another, whatever they carry."""
    return (naive(later) - naive(earlier)).days


def same_moment(left: datetime, right: datetime) -> bool:
    """Whether two moments are the same instant, however they say so.

    An equality that compares an aware moment with a naive one is
    always false, which is how a lifecycle lost track of the baseline
    it had just been given.
    """
    return naive(left) == naive(right)
