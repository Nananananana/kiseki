"""Retention is a rule about forgetting, and it is off by default."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import (
    SqliteCaptionRepository,
    SqlitePhotoRepository,
    SqliteProfileRepository,
    connect,
)
from kiseki.application.retention import (
    RetentionPolicy,
    apply_retention,
    plan_retention,
)
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.interests import Profile
from kiseki.domain.photo.observation import PhotoId, PhotoObservation

TODAY = datetime(2026, 8, 19, 12, tzinfo=UTC)


def _seeded(tmp_path: Path):
    connection = connect(tmp_path / "kiseki.sqlite3")
    photographs = [
        PhotoObservation(PhotoId(f"sha256:old{index}"), TODAY - timedelta(days=1200))
        for index in range(3)
    ] + [
        PhotoObservation(PhotoId(f"sha256:new{index}"), TODAY - timedelta(days=10))
        for index in range(2)
    ]
    SqlitePhotoRepository(connection).save_all(photographs)
    return connection


def test_a_policy_that_says_nothing_forgets_nothing(tmp_path: Path) -> None:
    connection = _seeded(tmp_path)
    plan = plan_retention(connection, RetentionPolicy(), TODAY)
    assert plan.is_empty


def test_the_default_policy_is_empty() -> None:
    assert RetentionPolicy().is_empty


def test_old_photographs_are_named_but_not_removed(tmp_path: Path) -> None:
    connection = _seeded(tmp_path)
    policy = RetentionPolicy(keep_photographs_for=timedelta(days=365))
    plan = plan_retention(connection, policy, TODAY)
    assert len(plan.photo_ids) == 3
    assert len(SqlitePhotoRepository(connection).all()) == 5


def test_applying_removes_exactly_those(tmp_path: Path) -> None:
    connection = _seeded(tmp_path)
    policy = RetentionPolicy(keep_photographs_for=timedelta(days=365))
    apply_retention(connection, policy, TODAY)
    remaining = SqlitePhotoRepository(connection).all()
    assert len(remaining) == 2
    assert all("new" in photo.photo_id.value for photo in remaining)


def test_a_refusal_can_be_let_go_of(tmp_path: Path) -> None:
    connection = _seeded(tmp_path)
    key = CaptionKey.of([PhotoId("sha256:new0")])
    SqliteCaptionRepository(connection).save(
        Caption(
            key=key,
            photo_ids=(PhotoId("sha256:new0"),),
            text="",
            model="",
            created_at=TODAY - timedelta(days=400),
            refused="no thumbnail",
        )
    )
    policy = RetentionPolicy(keep_refusals_for=timedelta(days=90))
    assert plan_retention(connection, policy, TODAY).refusals == 1
    apply_retention(connection, policy, TODAY)
    assert plan_retention(connection, policy, TODAY).refusals == 0


def test_the_readings_thin_to_one_a_month(tmp_path: Path) -> None:
    """A decade stays readable; the duplicates within a month do not."""
    connection = _seeded(tmp_path)
    profiles = SqliteProfileRepository(connection)
    for days in (400, 395, 390, 200, 195, 20, 10):
        profiles.save(Profile(generated_at=TODAY - timedelta(days=days), interests=()))
    policy = RetentionPolicy(keep_profiles=2)
    plan = plan_retention(connection, policy, TODAY)
    assert plan.profiles == 2
    apply_retention(connection, policy, TODAY)
    kept = profiles.history()
    assert len(kept) == 5


def test_keeping_none_is_not_a_policy() -> None:
    with pytest.raises(ValueError):
        RetentionPolicy(keep_profiles=0)


def test_a_span_of_no_time_is_not_a_span() -> None:
    with pytest.raises(ValueError):
        RetentionPolicy(keep_photographs_for=timedelta(0))
