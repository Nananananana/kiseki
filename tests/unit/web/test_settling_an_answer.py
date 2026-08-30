"""What the model said, made safe to record.

A model that ignores its instructions is a weaker classifier, not a
leak. Every rule here decides what is written down, which was never
the model's job.
"""

from kiseki_web.classifier import CATEGORIES, MAX_LABELS, UNLABELLED, asked_about, settle

MODEL = "a model"


def test_a_category_nobody_defined_becomes_other() -> None:
    assert settle("fascinating", ["a label"], MODEL).category == "other"


def test_the_categories_are_the_ones_the_contract_names() -> None:
    assert set(CATEGORIES) > UNLABELLED
    assert "other" in CATEGORIES


def test_a_category_that_carries_no_labels_loses_them() -> None:
    """Whatever the model said. The count is evidence; the labels would
    be the receipt, the diagnosis, or the politics."""
    for category in sorted(UNLABELLED):
        settled = settle(category, ["something specific", "and another"], MODEL)
        assert settled.category == category
        assert settled.labels == ()


def test_labels_are_tidied_rather_than_argued_with() -> None:
    settled = settle("reading", ["  Raft ", "raft", "", "Distributed  Systems"], MODEL)
    assert settled.labels == ("raft", "distributed systems")


def test_the_ninth_label_and_everything_after_it_goes() -> None:
    settled = settle("reading", [f"label {n}" for n in range(20)], MODEL)
    assert len(settled.labels) == MAX_LABELS


def test_the_model_is_shown_the_address_and_the_title() -> None:
    shown = asked_about("https://example.org/a", "A page")
    assert "https://example.org/a" in shown
    assert "A page" in shown


def test_a_page_with_no_title_is_asked_about_anyway() -> None:
    """Most of a browser history has one; some of it does not, and an
    address alone is still something to classify."""
    shown = asked_about("https://example.org/a", "   ")
    assert "https://example.org/a" in shown
    assert "title" not in shown
