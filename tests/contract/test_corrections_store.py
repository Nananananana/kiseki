"""Both correction stores honour the same append-only contract."""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.adapters.fake.corrections import FakeCorrectionRepository
from kiseki.adapters.sqlite.store import SqliteCorrectionRepository, connect
from kiseki.domain.correction import Correction, CorrectionVerdict

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _correction(minutes: int = 0, verdict: CorrectionVerdict = CorrectionVerdict.EXCLUDED):
    return Correction(
        reference="topic:data",
        verdict=verdict,
        note="generic label",
        created_at=WHEN + timedelta(minutes=minutes),
    )


@pytest.fixture(params=["fake", "sqlite"])
def repository(request, tmp_path):
    if request.param == "fake":
        return FakeCorrectionRepository()
    connection = connect(tmp_path / "kiseki.sqlite3")
    request.addfinalizer(connection.close)
    return SqliteCorrectionRepository(connection)


def test_an_empty_store_has_nothing(repository):
    assert repository.all() == ()


def test_a_correction_round_trips(repository):
    repository.add(_correction())
    assert repository.all() == (_correction(),)


def test_records_accumulate_and_keep_their_order(repository):
    repository.add(_correction(0))
    repository.add(_correction(1, CorrectionVerdict.REINSTATED))
    records = repository.all()
    assert len(records) == 2
    assert records[0].verdict is CorrectionVerdict.EXCLUDED
    assert records[1].verdict is CorrectionVerdict.REINSTATED
