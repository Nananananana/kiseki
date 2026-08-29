"""A comparison says how much of itself is vocabulary."""

import pytest
from kiseki.domain.services.vocabulary import SETTLED_SHARE, Overlap, overlap_of


def test_two_readings_that_agree_are_settled() -> None:
    overlap = overlap_of([(0.5, 0.6), (0.2, 0.3), (0.1, 0.1)])
    assert overlap.before == 3
    assert overlap.after == 3
    assert overlap.shared == 3
    assert overlap.share == 1.0
    assert overlap.settled
    assert overlap.caution == ""


def test_a_reading_that_learned_new_words_is_not_settled() -> None:
    """Nineteen topics against four hundred and ninety-eight, as it was."""
    rows = [(0.5, 0.5)] + [(0.0, 0.4)] * 20
    overlap = overlap_of(rows)
    assert overlap.before == 1
    assert overlap.after == 21
    assert overlap.shared == 1
    assert not overlap.settled
    assert "vocabulary changing" in overlap.caution


def test_a_topic_named_by_neither_counts_for_neither() -> None:
    overlap = overlap_of([(0.0, 0.0), (0.4, 0.4)])
    assert overlap.before == 1
    assert overlap.after == 1
    assert overlap.shared == 1


def test_the_threshold_is_where_it_says_it_is() -> None:
    # Eight shared out of ten named is settled; seven is not.
    settled = overlap_of([(0.5, 0.5)] * 8 + [(0.0, 0.5)] * 2)
    unsettled = overlap_of([(0.5, 0.5)] * 7 + [(0.0, 0.5)] * 3)
    assert settled.share >= SETTLED_SHARE
    assert unsettled.share < SETTLED_SHARE


def test_a_reading_that_forgot_words_is_not_settled_either() -> None:
    """One pair shrank and still shared only a third of its vocabulary."""
    overlap = overlap_of([(0.5, 0.5)] * 3 + [(0.5, 0.0)] * 7)
    assert not overlap.settled


def test_nothing_at_all_is_not_a_disagreement() -> None:
    overlap = overlap_of([])
    assert overlap.share == 1.0
    assert overlap.settled


def test_more_shared_than_held_is_impossible() -> None:
    with pytest.raises(ValueError):
        Overlap(before=2, after=3, shared=4)
