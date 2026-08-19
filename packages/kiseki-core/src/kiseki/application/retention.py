"""What a decade of readings should look like, decided in advance.

A library that only grows eventually holds a decade of somebody's
days, and nobody decided that -- it simply happened. So the shape is
chosen now, while the choice is cheap, and it is expressed as rules
about what to forget rather than as a machine that forgets.

Three rules, and every one of them is off by default. A library that
quietly discards the owner's past because a default said so would
break the promise the rest of this code keeps: what is stored is
theirs, and it goes when they say. Nothing here runs on a timer;
`kiseki retention` counts, and only `--apply` removes -- through the
same path a deliberate deletion takes (ADR-0061).

    keep_photographs_for  forget photographs older than this
    keep_refusals_for     forget refusals older than this
    keep_profiles         keep the recent readings, and one per month
                          before them

The profile rule keeps the shape of a history rather than a window of
it: the trend, the lifecycle and the comparison all read across
years, and thinning to one reading a month leaves them a decade to
read while holding a fraction of the rows. See ADR-0062.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from kiseki.domain.shared.moment import naive


@dataclass(frozen=True)
class RetentionPolicy:
    """What to keep. Every rule is off unless the owner sets it."""

    keep_photographs_for: timedelta | None = None
    keep_refusals_for: timedelta | None = None
    keep_profiles: int | None = None

    def __post_init__(self) -> None:
        for label, span in (
            ("keep_photographs_for", self.keep_photographs_for),
            ("keep_refusals_for", self.keep_refusals_for),
        ):
            if span is not None and span <= timedelta(0):
                raise ValueError(f"{label} must be a span of time, or nothing at all")
        if self.keep_profiles is not None and self.keep_profiles < 1:
            raise ValueError("keeping no readings at all is not a retention policy")

    @property
    def is_empty(self) -> bool:
        return (
            self.keep_photographs_for is None
            and self.keep_refusals_for is None
            and self.keep_profiles is None
        )


@dataclass(frozen=True)
class RetentionPlan:
    """What the rules would forget, counted before anything does."""

    photo_ids: tuple[str, ...]
    refusals: int
    profiles: int

    @property
    def is_empty(self) -> bool:
        return not self.photo_ids and not self.refusals and not self.profiles


REFUSAL_TABLES = ("captions", "subjects", "screen_readings", "single_captions")


def _naive(moment: datetime) -> datetime:
    return naive(moment)


def _older_photographs(connection: sqlite3.Connection, cutoff: datetime) -> tuple[str, ...]:
    rows = connection.execute("SELECT id, captured_at FROM photos ORDER BY id")
    return tuple(
        identifier
        for identifier, captured in rows
        if _naive(datetime.fromisoformat(captured)) < _naive(cutoff)
    )


def _older_refusals(connection: sqlite3.Connection, cutoff: datetime) -> int:
    total = 0
    for table in REFUSAL_TABLES:
        try:
            rows = connection.execute(
                f"SELECT created_at FROM {table} WHERE refused IS NOT NULL"
            ).fetchall()
        except sqlite3.OperationalError:
            continue
        total += sum(
            1 for (created,) in rows if _naive(datetime.fromisoformat(created)) < _naive(cutoff)
        )
    return total


def _thinnable_profiles(connection: sqlite3.Connection, keep: int) -> tuple[str, ...]:
    """The kept readings a policy would let go: the older duplicates.

    The most recent `keep` readings stay, and before them the first
    reading of each month stays. What goes is the second and third
    reading of a month long past, which say nothing the first does not.
    """
    rows = connection.execute(
        "SELECT generated_at FROM profiles ORDER BY generated_at DESC"
    ).fetchall()
    recent = {row[0] for row in rows[:keep]}
    seen_months: set[str] = set()
    doomed: list[str] = []
    for (generated,) in reversed(rows):
        if generated in recent:
            continue
        month = generated[:7]
        if month in seen_months:
            doomed.append(generated)
        else:
            seen_months.add(month)
    return tuple(doomed)


def plan_retention(
    connection: sqlite3.Connection,
    policy: RetentionPolicy,
    today: datetime,
) -> RetentionPlan:
    """What the rules would forget. Counts only; removes nothing."""
    if policy.is_empty:
        return RetentionPlan((), 0, 0)
    photographs: tuple[str, ...] = ()
    if policy.keep_photographs_for is not None:
        photographs = _older_photographs(connection, today - policy.keep_photographs_for)
    refusals = 0
    if policy.keep_refusals_for is not None:
        refusals = _older_refusals(connection, today - policy.keep_refusals_for)
    profiles: tuple[str, ...] = ()
    if policy.keep_profiles is not None:
        profiles = _thinnable_profiles(connection, policy.keep_profiles)
    return RetentionPlan(photo_ids=photographs, refusals=refusals, profiles=len(profiles))


def apply_retention(
    connection: sqlite3.Connection,
    policy: RetentionPolicy,
    today: datetime,
) -> RetentionPlan:
    """Remove what the rules chose, through the ordinary paths.

    Photographs go through the deletion that reaches everything that
    spoke about them (ADR-0061); refusals and surplus readings are rows
    with nothing derived from them, and go directly.
    """
    from kiseki.application.forgetting import forget, plan_forget

    plan = plan_retention(connection, policy, today)
    if plan.is_empty:
        return plan
    if plan.photo_ids:
        forget(connection, plan_forget(connection, plan.photo_ids))
    if policy.keep_refusals_for is not None:
        cutoff = (today - policy.keep_refusals_for).replace(tzinfo=None).isoformat()
        with connection:
            for table in REFUSAL_TABLES:
                try:
                    connection.execute(
                        f"DELETE FROM {table} WHERE refused IS NOT NULL AND created_at < ?",
                        (cutoff,),
                    )
                except sqlite3.OperationalError:
                    continue
    if policy.keep_profiles is not None:
        doomed = _thinnable_profiles(connection, policy.keep_profiles)
        if doomed:
            marks = ",".join("?" for _ in doomed)
            with connection:
                connection.execute(f"DELETE FROM profiles WHERE generated_at IN ({marks})", doomed)
    return plan


def _spans(values: Sequence[str]) -> None:  # pragma: no cover - documentation only
    """Reserved: parsing "2 years" from a configuration file, in v0.10."""
