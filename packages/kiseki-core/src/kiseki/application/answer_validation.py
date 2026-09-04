"""Checks an answer past the shape of it.

The answer contract already requires citations (ADR-0038); a
contract is only kept if someone checks. A citation can point at a
fact that does not exist, a claim can carry a year no evidence ever
saw, and a fluent paragraph can cite nothing at all -- each of those
parses perfectly and says something the evidence does not.

Nothing is rewritten here. The model's answer is kept exactly as it
came, and the defects are reported beside it: the same posture as
corrections and the stoplist -- store what was said, judge at
reading time. Rejecting an answer outright is a v0.8 decision, once
the real rate of each defect is known. See ADR-0054.
"""

from __future__ import annotations

import re
from enum import Enum, unique

from kiseki.application.asking import Answer

MOMENT_GROUP = re.compile(r"\[\s*F\s*\d+(?:\s*,\s*F?\s*\d+)*\s*\]")
"""Readers cite one fact per bracket, and models group them:
"[F1][F5]" and "[F1, F5]" say the same thing, so the check reads
both. Anything looser is not a citation, and the answer is told so
rather than being given the benefit of the doubt."""

PATTERN_GROUP = re.compile(r"\[\s*G\s*\d+(?:\s*,\s*G?\s*\d+)*\s*\]")
"""The same, for the patterns a grounded answer cites.

Added when `ask` gained a second closed list. Without it, an answer
citing `[G1][G2]` -- correctly, and from the derivation that actually
held the answer -- was reported as citing nothing at all, which is
the check being wrong about a correct answer. **A validator that
does not know about a kind of evidence reports every use of it as a
defect**, and that is worse than not checking: it teaches a reader to
ignore the check."""

CITATION_GROUP = MOMENT_GROUP
"""Kept under its old name for anything that imported it."""

NUMBER = re.compile(r"\d+")
YEAR = re.compile(r"(?<!\d)(19|20)(\d{2})(?!\d)")


@unique
class AnswerDefect(Enum):
    """What can be wrong with an answer that still parses."""

    UNCITED = "the answer cites no evidence"
    UNKNOWN_CITATION = "the answer cites a fact that does not exist"
    UNSEEN_YEAR = "the answer names a year the evidence never saw"


def _cited(answer: Answer, pattern: re.Pattern[str]) -> list[int]:
    return [
        int(number) for group in pattern.findall(answer.answer) for number in NUMBER.findall(group)
    ]


def validate_answer(answer: Answer) -> tuple[AnswerDefect, ...]:
    """The defects this answer carries, in a fixed order."""
    if not answer.answer.strip() or not answer.answered:
        return ()

    defects: list[AnswerDefect] = []
    moments = _cited(answer, MOMENT_GROUP)
    patterns = _cited(answer, PATTERN_GROUP)
    if not moments and not patterns:
        defects.append(AnswerDefect.UNCITED)
    elif any(number < 1 or number > len(answer.evidence) for number in moments) or any(
        number < 1 or number > len(answer.grounding) for number in patterns
    ):
        defects.append(AnswerDefect.UNKNOWN_CITATION)

    # Only the moments have years to compare against. A pattern
    # spanning a period would make almost any year defensible, so it
    # is left out rather than used to widen the check into nothing.
    seen = {item.document.observed_at.year for item in answer.evidence}
    seen |= {fact.observed_at.year for fact in answer.grounding if fact.observed_at is not None}
    # A pattern's text carries the dates it spans -- "19 outings between
    # 2025-07-31 and 2026-09-04" -- and those years are as real as a
    # timestamp: this repository wrote that sentence from its own data,
    # not a model. Without reading them, an answer correctly citing the
    # span of a pattern was reported for naming a year the evidence
    # never saw. Measured: that false positive appeared on the first
    # grounded run, on a correct answer.
    seen |= {
        int(f"{century}{rest}")
        for fact in answer.grounding
        for century, rest in YEAR.findall(fact.text)
    }
    named = {int(f"{century}{rest}") for century, rest in YEAR.findall(answer.answer)}
    if seen and named and not named <= seen:
        defects.append(AnswerDefect.UNSEEN_YEAR)
    return tuple(defects)
