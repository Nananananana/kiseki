"""Reads a time window out of a question, deterministically.

A closed list of Japanese and English expressions becomes a
since/until pair; anything else adds no window, which is better than
guessing. No model is involved: the same question and the same clock
always give the same window. The clock must be timezone aware,
because the window is compared with timezone-aware observation
times. Japanese literals are written as escapes so the file stays
ASCII; they are the same strings at runtime. See ADR-0039.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

RECENT_DAYS = 90
"""What "recently" means, in days. A named constant, not a guess."""

MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

_MONTH_NAME_PATTERN = "|".join(MONTH_NAMES)

# kyonen / sakunen (last year), issakunen (the year before last),
# kotoshi (this year), sengetsu / kongetsu (last / this month),
# senshuu / konshuu (last / this week), kinou / kyou (yesterday /
# today), saikin (recently), N-gatsu, YYYY-nen, koko / kono / kako /
# chokkin N units.
_KYONEN = "\u53bb\u5e74"
_SAKUNEN = "\u6628\u5e74"
_ISSAKUNEN = "\u4e00\u6628\u5e74"
_KOTOSHI = "\u4eca\u5e74"
_SENGETSU = "\u5148\u6708"
_KONGETSU = "\u4eca\u6708"
_SENSHUU = "\u5148\u9031"
_KONSHUU = "\u4eca\u9031"
_KINOU = "\u6628\u65e5"
_KYOU = "\u4eca\u65e5"
_SAIKIN = "\u6700\u8fd1"

_YEAR_MONTH_JA = re.compile(r"(\d{4})\u5e74\s*(\d{1,2})\u6708")
_YEAR_JA = re.compile(r"(\d{4})\u5e74")
_BARE_MONTH_JA = re.compile(r"(?<!\d)(\d{1,2})\u6708")
_RELATIVE_JA = re.compile(
    r"(?:\u3053\u3053|\u3053\u306e|\u904e\u53bb|\u76f4\u8fd1)\s*(\d+)\s*"
    r"(\u65e5|\u9031\u9593|[\u30f6\u30b1\u304b]\u6708|\u5e74)"
)
_RELATIVE_EN = re.compile(r"last\s+(\d+)\s+(day|week|month|year)s?")
_YEAR_EN = re.compile(r"\b(19\d{2}|20\d{2})\b")

_DAY_UNITS = ("\u65e5", "day")
_WEEK_UNITS = ("\u9031\u9593", "week")
_YEAR_UNITS = ("\u5e74", "year")


@dataclass(frozen=True)
class TimeWindow:
    """An inclusive since/until pair, timezone aware."""

    since: datetime
    until: datetime


def read_time_window(text: str, now: datetime) -> TimeWindow | None:
    """The window the question asks for, or None when it asks for none."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone aware")
    lowered = text.lower()

    match = _YEAR_MONTH_JA.search(text)
    if match:
        return _month(int(match.group(1)), int(match.group(2)), now)
    match = re.search(rf"\b({_MONTH_NAME_PATTERN})\s+(\d{{4}})\b", lowered)
    if match:
        return _month(int(match.group(2)), MONTH_NAMES[match.group(1)], now)

    last_year = (
        _KYONEN in text or _SAKUNEN in text or "last year" in lowered
    ) and _ISSAKUNEN not in text
    month_match = _BARE_MONTH_JA.search(text)
    if month_match:
        month = int(month_match.group(1))
        if 1 <= month <= 12:
            if last_year:
                return _month(now.year - 1, month, now)
            year = now.year if month <= now.month else now.year - 1
            return _month(year, month, now)

    if _ISSAKUNEN in text:
        return _year(now.year - 2, now)
    if last_year:
        return _year(now.year - 1, now)
    if _KOTOSHI in text or "this year" in lowered:
        return _year(now.year, now)
    match = _YEAR_JA.search(text) or _YEAR_EN.search(lowered)
    if match:
        return _year(int(match.group(1)), now)

    if _SENGETSU in text or "last month" in lowered:
        year, month = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
        return _month(year, month, now)
    if _KONGETSU in text or "this month" in lowered:
        return _month(now.year, now.month, now)
    if _SENSHUU in text or "last week" in lowered:
        start = _week_start(now) - timedelta(days=7)
        return TimeWindow(start, start + timedelta(days=7) - timedelta(seconds=1))
    if _KONSHUU in text or "this week" in lowered:
        return TimeWindow(_week_start(now), now)
    if _KINOU in text or "yesterday" in lowered:
        start = _day_start(now) - timedelta(days=1)
        return TimeWindow(start, start + timedelta(days=1) - timedelta(seconds=1))
    if _KYOU in text or "today" in lowered:
        return TimeWindow(_day_start(now), now)

    match = _RELATIVE_JA.search(text) or _RELATIVE_EN.search(lowered)
    if match:
        return _relative(int(match.group(1)), match.group(2), now)
    if _SAIKIN in text or "recently" in lowered or "lately" in lowered:
        return TimeWindow(now - timedelta(days=RECENT_DAYS), now)
    return None


def _relative(amount: int, unit: str, now: datetime) -> TimeWindow:
    if unit in _DAY_UNITS:
        days = amount
    elif unit in _WEEK_UNITS:
        days = amount * 7
    elif unit in _YEAR_UNITS:
        days = amount * 365
    else:
        days = amount * 30
    return TimeWindow(now - timedelta(days=days), now)


def _year(year: int, now: datetime) -> TimeWindow:
    tz = now.tzinfo
    return TimeWindow(
        datetime(year, 1, 1, tzinfo=tz),
        datetime(year, 12, 31, 23, 59, 59, tzinfo=tz),
    )


def _month(year: int, month: int, now: datetime) -> TimeWindow:
    tz = now.tzinfo
    last_day = calendar.monthrange(year, month)[1]
    return TimeWindow(
        datetime(year, month, 1, tzinfo=tz),
        datetime(year, month, last_day, 23, 59, 59, tzinfo=tz),
    )


def _week_start(now: datetime) -> datetime:
    return _day_start(now) - timedelta(days=now.weekday())


def _day_start(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)
