"""Two moments may disagree about time zones and still be compared."""

from datetime import UTC, datetime, timedelta, timezone

from kiseki.domain.shared.moment import days_between, naive, same_moment

TOKYO = timezone(timedelta(hours=9))


def test_a_naive_moment_is_left_alone() -> None:
    moment = datetime(2026, 6, 1, 12)
    assert naive(moment) is moment or naive(moment) == moment
    assert naive(moment).tzinfo is None


def test_an_aware_moment_loses_only_its_zone() -> None:
    moment = datetime(2026, 6, 1, 12, tzinfo=UTC)
    assert naive(moment).tzinfo is None


def test_days_between_survives_a_mixture() -> None:
    aware = datetime(2026, 6, 1, 12, tzinfo=UTC)
    later = datetime(2026, 6, 11, 12)
    assert days_between(aware, later) in (9, 10)


def test_days_between_two_aware_moments_is_exact() -> None:
    first = datetime(2026, 6, 1, 12, tzinfo=TOKYO)
    second = datetime(2026, 6, 21, 12, tzinfo=TOKYO)
    assert days_between(first, second) == 20


def test_the_same_instant_is_the_same_moment_either_way() -> None:
    aware = datetime(2026, 6, 1, 3, tzinfo=UTC)
    assert same_moment(aware, naive(aware))


def test_different_moments_are_not_the_same() -> None:
    first = datetime(2026, 6, 1, 12, tzinfo=UTC)
    second = datetime(2026, 6, 2, 12, tzinfo=UTC)
    assert not same_moment(first, second)
