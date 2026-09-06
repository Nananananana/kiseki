"""A kept profile is stamped with its offset, and the store refuses one
without (#402, ADR-0064).

Every kept profile on the real library lacked an offset while every
photograph carried one. Old rows stay readable; new ones say where
they were made; and a history holding both still pairs for a trend.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.adapters.sqlite.store import SqliteProfileRepository, _profile_document, connect
from kiseki.application.pipeline import Pipeline
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence, Profile

JST = timezone(timedelta(hours=9))


def _interest(topic: str, at: datetime) -> Interest:
    return Interest(
        topic=topic,
        score=0.9,
        confidence=0.6,
        evidence=(
            InterestEvidence(
                kind=EvidenceKind.PHOTOGRAPH, reference=f"caption:{topic}", observed_at=at
            ),
        ),
        first_seen=at,
        last_seen=at,
    )


def test_the_pipeline_stamps_a_kept_profile_with_an_offset(tmp_path: Path) -> None:
    connection = connect(tmp_path / "k.sqlite3")
    profiles = SqliteProfileRepository(connection)
    pipeline = Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        profiles=profiles,
    )
    pipeline.profile(keep=True)
    (stored,) = connection.execute("SELECT generated_at FROM profiles").fetchone()
    parsed = datetime.fromisoformat(stored)
    assert parsed.tzinfo is not None, f"stored without an offset: {stored}"


def test_the_store_refuses_a_naive_stamp(tmp_path: Path) -> None:
    connection = connect(tmp_path / "k.sqlite3")
    naive = Profile(generated_at=datetime(2026, 9, 6, 12, 0), interests=())
    with pytest.raises(ValueError, match="offset"):
        SqliteProfileRepository(connection).save(naive)


def test_an_old_naive_row_and_a_new_aware_one_still_pair_for_a_trend(tmp_path: Path) -> None:
    """What every existing library holds: rows stamped before #402, then
    rows stamped after. The pair for a trend must still be found."""
    connection = connect(tmp_path / "k.sqlite3")
    old_when = datetime(2026, 8, 1, 12, 0)  # naive, as the real rows are
    old = Profile(
        generated_at=old_when,
        interests=(_interest("raft", datetime(2026, 8, 1, 12, 0, tzinfo=JST)),),
    )
    with connection:
        connection.execute(
            "INSERT INTO profiles (generated_at, document) VALUES (?, ?)",
            (old_when.isoformat(), json.dumps(_profile_document(old))),
        )
    profiles = SqliteProfileRepository(connection)
    new_when = datetime(2026, 9, 6, 12, 0, tzinfo=JST)
    profiles.save(
        Profile(
            generated_at=new_when,
            interests=(_interest("raft", new_when), _interest("camping", new_when)),
        )
    )
    pipeline = Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        profiles=profiles,
    )
    comparison = pipeline.compare()
    assert comparison is not None, "the mixed history could not be paired"
    assert {entry.topic for entry in comparison.entries} >= {"raft", "camping"}
    assert pipeline.trend() is not None
    assert pipeline.lifecycle() is not None
