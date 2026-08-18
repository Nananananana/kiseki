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

CITATION_GROUP = re.compile(r"\[\s*F\s*\d+(?:\s*,\s*F?\s*\d+)*\s*\]")
"""Readers cite one fact per bracket, and models group them:
"[F1][F5]" and "[F1, F5]" say the same thing, so the check reads
both. Anything looser is not a citation, and the answer is told so
rather than being given the benefit of the doubt."""

NUMBER = re.compile(r"\d+")
YEAR = re.compile(r"(?<!\d)(19|20)(\d{2})(?!\d)")


@unique
class AnswerDefect(Enum):
    """What can be wrong with an answer that still parses."""

    UNCITED = "the answer cites no evidence"
    UNKNOWN_CITATION = "the answer cites a fact that does not exist"
    UNSEEN_YEAR = "the answer names a year the evidence never saw"


def validate_answer(answer: Answer) -> tuple[AnswerDefect, ...]:
    """The defects this answer carries, in a fixed order."""
    if not answer.answer.strip() or not answer.evidence:
        return ()

    defects: list[AnswerDefect] = []
    cited = [
        int(number)
        for group in CITATION_GROUP.findall(answer.answer)
        for number in NUMBER.findall(group)
    ]
    if not cited:
        defects.append(AnswerDefect.UNCITED)
    elif any(number < 1 or number > len(answer.evidence) for number in cited):
        defects.append(AnswerDefect.UNKNOWN_CITATION)

    seen = {item.document.observed_at.year for item in answer.evidence}
    named = {int(f"{century}{rest}") for century, rest in YEAR.findall(answer.answer)}
    if named and not named <= seen:
        defects.append(AnswerDefect.UNSEEN_YEAR)
    return tuple(defects)
