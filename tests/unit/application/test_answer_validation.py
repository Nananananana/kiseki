"""A schema-valid answer can still be an unsupported one."""

from datetime import UTC, datetime

from kiseki.application.answer_validation import AnswerDefect, validate_answer
from kiseki.application.asking import Answer
from kiseki.application.grounding import Grounding
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


class TestAnAnswerThatCitesPatterns:
    """`ask` gained a second closed list, and the validator did not
    know about it.

    An answer citing `[G1][G2]` -- correctly, and from the derivation
    that actually held the answer -- was reported as citing nothing at
    all. **A validator that does not know about a kind of evidence
    reports every use of it as a defect**, which is worse than not
    checking: it teaches a reader to ignore the check.

    Measured on the first grounded run: the answer was right, cited
    two patterns, and printed `check  the answer cites no evidence`.
    """

    def a_pattern(self) -> Grounding:
        return Grounding(
            kind="place",
            text="Place 1: returned to on 12 separate days.",
            source="kiseki places",
            observed_at=WHEN,
        )

    def grounded(self, text: str, patterns: int = 2) -> Answer:
        return Answer(
            question="where do I keep going back to?",
            answer=text,
            confidence=0.5,
            first_seen=WHEN,
            last_seen=WHEN,
            evidence=(),
            model="a stand-in",
            grounding=tuple(self.a_pattern() for _ in range(patterns)),
        )

    def test_citing_a_pattern_is_citing(self) -> None:
        assert validate_answer(self.grounded("You go back often [G1][G2].")) == ()

    def test_citing_nothing_is_still_a_defect(self) -> None:
        assert AnswerDefect.UNCITED in validate_answer(self.grounded("You go back often."))

    def test_citing_a_pattern_that_does_not_exist_is_caught(self) -> None:
        defects = validate_answer(self.grounded("You go back often [G9].", patterns=2))
        assert AnswerDefect.UNKNOWN_CITATION in defects

    def test_a_grouped_citation_counts(self) -> None:
        assert validate_answer(self.grounded("You go back often [G1, G2].")) == ()

    def test_an_answer_with_nothing_at_all_is_not_judged(self) -> None:
        """No evidence and no patterns: there was no model call, so
        there is nothing to be wrong."""
        empty = Answer("q", "", 0.0, None, None, (), "")
        assert validate_answer(empty) == ()

    def test_a_year_a_pattern_names_is_a_year_the_evidence_saw(self) -> None:
        """A pattern's text carries the dates it spans, and this
        repository wrote that sentence from its own data. Without
        reading them, an answer correctly citing a pattern's span was
        reported for naming a year the evidence never saw -- which
        happened on the first grounded run."""
        spanning = Grounding(
            kind="rhythm",
            text="19 outings between 2025-07-31 and 2026-09-04.",
            source="kiseki report",
            observed_at=WHEN,
        )
        answer = Answer(
            question="am I going out less than last year?",
            answer="You made 19 outings from 2025 onwards [G1].",
            confidence=0.5,
            first_seen=WHEN,
            last_seen=WHEN,
            evidence=(),
            model="a stand-in",
            grounding=(spanning,),
        )
        assert AnswerDefect.UNSEEN_YEAR not in validate_answer(answer)

    def test_a_year_nothing_saw_is_still_caught(self) -> None:
        """The check has to keep its teeth. 1999 is in no fact."""
        answer = self.grounded("You went there in 1999 [G1].")
        assert AnswerDefect.UNSEEN_YEAR in validate_answer(answer)
