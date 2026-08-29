"""Reading the same day twice says nothing the first reading did not."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from kiseki.adapters.sqlite.store import SqliteProfileRepository, connect
from kiseki.application.retention import (
    RetentionPolicy,
    apply_retention,
    plan_retention,
)
from kiseki.domain.interests import Profile

NOW = datetime(2026, 8, 29, 18, tzinfo=UTC)


def _seeded(tmp_path: Path, moments: tuple[datetime, ...]):
    connection = connect(tmp_path / "kiseki.sqlite3")
    profiles = SqliteProfileRepository(connection)
    for moment in moments:
        profiles.save(Profile(generated_at=moment, interests=()))
    return connection


def _days(connection) -> list[str]:
    return [
        row[0][:10]
        for row in connection.execute("SELECT generated_at FROM profiles ORDER BY generated_at")
    ]


def test_a_day_keeps_its_first_reading(tmp_path: Path) -> None:
    connection = _seeded(
        tmp_path,
        (
            NOW - timedelta(days=2, hours=3),
            NOW - timedelta(days=2, hours=1),
            NOW - timedelta(days=1),
            NOW - timedelta(hours=5),
            NOW - timedelta(hours=4),
            NOW - timedelta(hours=3),
        ),
    )
    policy = RetentionPolicy(one_a_day=True)
    assert plan_retention(connection, policy, NOW).profiles == 3
    apply_retention(connection, policy, NOW)
    assert _days(connection) == sorted(set(_days(connection)))
    assert len(_days(connection)) == 3


def test_one_reading_a_day_already_is_nothing_to_forget(tmp_path: Path) -> None:
    connection = _seeded(tmp_path, (NOW - timedelta(days=2), NOW - timedelta(days=1), NOW))
    assert plan_retention(connection, RetentionPolicy(one_a_day=True), NOW).profiles == 0


def test_the_rule_is_off_unless_asked_for(tmp_path: Path) -> None:
    connection = _seeded(tmp_path, (NOW - timedelta(hours=2), NOW - timedelta(hours=1), NOW))
    assert RetentionPolicy().is_empty
    assert plan_retention(connection, RetentionPolicy(), NOW).is_empty
    assert len(_days(connection)) == 3


def test_the_earliest_of_a_day_is_the_one_that_stays(tmp_path: Path) -> None:
    first = NOW - timedelta(hours=9)
    connection = _seeded(tmp_path, (first, NOW - timedelta(hours=4), NOW))
    apply_retention(connection, RetentionPolicy(one_a_day=True), NOW)
    rows = [row[0] for row in connection.execute("SELECT generated_at FROM profiles")]
    assert len(rows) == 1
    assert rows[0].startswith(first.isoformat()[:16])


def test_the_two_profile_rules_do_not_double_count(tmp_path: Path) -> None:
    """A reading both rules would drop is dropped once."""
    connection = _seeded(
        tmp_path,
        (
            NOW - timedelta(days=200, hours=3),
            NOW - timedelta(days=200, hours=1),
            NOW - timedelta(days=1),
            NOW,
        ),
    )
    policy = RetentionPolicy(one_a_day=True, keep_profiles=2)
    plan = plan_retention(connection, policy, NOW)
    assert plan.profiles == 1
    apply_retention(connection, policy, NOW)
    remaining = connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
    assert remaining == 3
