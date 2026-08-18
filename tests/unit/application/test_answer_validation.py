"""A schema-valid answer can still be an unsupported one."""

from datetime import UTC, datetime

from kiseki.application.answer_validation import AnswerDefect, validate_answer
from kiseki.application.asking import Answer
from kiseki.application.retrieval import Retrieval
from kiseki.ports.search import SearchDocument

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


def _evidence(count: int) -> tuple[Retrieval, ...]:
    return tuple(
        Retrieval(
            SearchDocument(f"stay:{index}", "stay", "a bowl of ramen", WHEN),
            1.0 / (index + 1),
            ("words",),
        )
        for index in range(count)
    )


def _answer(text: str, count: int = 2) -> Answer:
    return Answer(
        "what did I eat?",
        text,
        0.5,
        WHEN,
        WHEN,
        _evidence(count),
        "lm",
    )


def test_a_supported_answer_has_no_defects() -> None:
    assert validate_answer(_answer("ramen, twice [F1][F2]")) == ()


def test_an_answer_without_a_citation_is_a_defect() -> None:
    assert validate_answer(_answer("ramen, twice")) == (AnswerDefect.UNCITED,)


def test_a_citation_beyond_the_evidence_is_a_defect() -> None:
    assert AnswerDefect.UNKNOWN_CITATION in validate_answer(_answer("ramen [F9]"))


def test_a_zero_citation_is_a_defect() -> None:
    assert AnswerDefect.UNKNOWN_CITATION in validate_answer(_answer("ramen [F0]"))


def test_a_year_the_evidence_never_saw_is_a_defect() -> None:
    defects = validate_answer(_answer("ramen in 2019 [F1]"))
    assert AnswerDefect.UNSEEN_YEAR in defects


def test_the_evidence_s_own_year_is_fine() -> None:
    assert validate_answer(_answer("ramen in 2026 [F1]")) == ()


def test_an_empty_answer_is_left_alone() -> None:
    assert validate_answer(_answer("", count=0)) == ()

def test_a_grouped_citation_counts() -> None:
    assert validate_answer(_answer("ramen and toast [F1, F2]")) == ()


def test_a_tight_group_counts_too() -> None:
    assert validate_answer(_answer("ramen and toast [F1,F2]")) == ()


def test_a_grouped_citation_beyond_the_evidence_is_still_a_defect() -> None:
    defects = validate_answer(_answer("ramen and toast [F1, F9]"))
    assert AnswerDefect.UNKNOWN_CITATION in defects
