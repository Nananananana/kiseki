"""A closed list of time expressions becomes a window, deterministically.

Japanese literals are written as escapes so every file stays ASCII;
they are the same strings at runtime.
"""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.domain.services.time_expressions import read_time_window

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)

KYONEN = "\u53bb\u5e74"
SAKUNEN = "\u6628\u5e74"
ISSAKUNEN = "\u4e00\u6628\u5e74"
KOTOSHI = "\u4eca\u5e74"
SENGETSU = "\u5148\u6708"
SENSHUU = "\u5148\u9031"
SAIKIN = "\u6700\u8fd1"
NEN = "\u5e74"
GATSU = "\u6708"
KOKO = "\u3053\u3053"
NICHI = "\u65e5"
NO = "\u306e"


def test_last_year_ja():
    for text in (KYONEN + " ramen", SAKUNEN + " ramen"):
        window = read_time_window(text, NOW)
        assert window is not None
        assert window.since == datetime(2025, 1, 1, tzinfo=UTC)
        assert window.until == datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)


def test_the_year_before_last():
    window = read_time_window(ISSAKUNEN + " trip", NOW)
    assert window is not None
    assert window.since.year == 2024
    assert window.until.year == 2024


def test_this_year():
    window = read_time_window(KOTOSHI + " trend", NOW)
    assert window is not None
    assert window.since == datetime(2026, 1, 1, tzinfo=UTC)


def test_a_specific_year():
    window = read_time_window("2025" + NEN + " ?", NOW)
    assert window is not None
    assert window.since.year == 2025
    assert window.until == datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)


def test_a_specific_month_ja():
    window = read_time_window("2025" + NEN + "5" + GATSU + " photos", NOW)
    assert window is not None
    assert window.since == datetime(2025, 5, 1, tzinfo=UTC)
    assert window.until == datetime(2025, 5, 31, 23, 59, 59, tzinfo=UTC)


def test_a_bare_month_looks_back():
    window = read_time_window("11" + GATSU + " ?", NOW)
    assert window is not None
    assert window.since == datetime(2025, 11, 1, tzinfo=UTC)


def test_last_year_with_a_month():
    window = read_time_window(KYONEN + NO + "5" + GATSU, NOW)
    assert window is not None
    assert window.since == datetime(2025, 5, 1, tzinfo=UTC)


def test_last_month_crosses_the_year():
    january = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    window = read_time_window(SENGETSU + " meals", january)
    assert window is not None
    assert window.since == datetime(2025, 12, 1, tzinfo=UTC)
    assert window.until == datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)


def test_last_week_starts_on_monday():
    window = read_time_window(SENSHUU + " ?", NOW)
    assert window is not None
    assert window.since == datetime(2026, 8, 3, tzinfo=UTC)
    assert window.until == datetime(2026, 8, 9, 23, 59, 59, tzinfo=UTC)


def test_relative_days_ja():
    window = read_time_window(KOKO + "30" + NICHI, NOW)
    assert window is not None
    assert window.since == NOW - timedelta(days=30)
    assert window.until == NOW


def test_relative_weeks_en():
    window = read_time_window("what happened in the last 2 weeks?", NOW)
    assert window is not None
    assert window.since == NOW - timedelta(days=14)


def test_recently_means_ninety_days():
    window = read_time_window(SAIKIN + " ramen", NOW)
    assert window is not None
    assert window.since == NOW - timedelta(days=90)
    assert window.until == NOW


def test_an_english_month_and_year():
    window = read_time_window("what did I photograph in May 2025?", NOW)
    assert window is not None
    assert window.since == datetime(2025, 5, 1, tzinfo=UTC)


def test_english_last_year():
    window = read_time_window("what changed last year?", NOW)
    assert window is not None
    assert window.since.year == 2025


def test_no_expression_means_no_window():
    assert read_time_window("just ramen photos", NOW) is None


def test_a_naive_clock_is_refused():
    with pytest.raises(ValueError):
        read_time_window(KYONEN, datetime(2026, 8, 16, 12, 0))
