"""Corrections are append-only; the latest word per reference wins."""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.domain.correction import (
    Correction,
    CorrectionVerdict,
    active_exclusions,
)

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _correction(reference: str, verdict: CorrectionVerdict, minutes: int = 0) -> Correction:
    return Correction(
        reference=reference,
        verdict=verdict,
        note="",
        created_at=WHEN + timedelta(minutes=minutes),
    )


def test_a_correction_needs_a_reference():
    with pytest.raises(ValueError):
        _correction("  ", CorrectionVerdict.EXCLUDED)


def test_an_exclusion_is_active():
    active = active_exclusions([_correction("topic:data", CorrectionVerdict.EXCLUDED)])
    assert active == frozenset({"topic:data"})


def test_a_reinstatement_clears_the_exclusion():
    active = active_exclusions(
        [
            _correction("topic:data", CorrectionVerdict.EXCLUDED, 0),
            _correction("topic:data", CorrectionVerdict.REINSTATED, 1),
        ]
    )
    assert active == frozenset()


def test_the_latest_word_wins_regardless_of_input_order():
    active = active_exclusions(
        [
            _correction("topic:data", CorrectionVerdict.EXCLUDED, 2),
            _correction("topic:data", CorrectionVerdict.REINSTATED, 1),
        ]
    )
    assert active == frozenset({"topic:data"})
