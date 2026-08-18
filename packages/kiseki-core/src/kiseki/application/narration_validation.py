"""Checks a narration against the facts it was given.

The narration stage hands the model a closed, numbered list and asks
for prose that cites it (ADR-0022). Nothing checked that the prose kept
the bargain. Real output showed two ways it does not: a citation
written as a range, "[F10-F16]", which the answer check would have read
as no citation at all; and a number the facts never state -- the facts
said 82 per cent were never returned to, and the story said 18 per cent
were revisited. The arithmetic is right and the claim is not in
evidence, which is exactly the distinction this library exists to keep.

Three defects, deterministic and without a model. The narration itself
is never rewritten: the model said what it said, and the check says
what is wrong with it -- the posture of ADR-0044, ADR-0053 and
ADR-0054. See ADR-0057.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from enum import Enum, unique

CITATION = re.compile(r"\[\s*F\s*(\d+)(?:\s*(?:,|-|--|to)\s*F?\s*(\d+))*\s*\]")
CITATION_NUMBERS = re.compile(r"\d+")
NUMBER = re.compile(r"\d[\d,._]*")

MIN_CHECKED_DIGITS = 2
"""Single digits appear everywhere and mean little; checking them would
report a defect for the word "two"."""


@unique
class NarrationDefect(Enum):
    """What can be wrong with prose that reads perfectly well."""

    UNCITED = "the narration cites no fact"
    UNKNOWN_CITATION = "the narration cites a fact that does not exist"
    UNSUPPORTED_NUMBER = "the narration states a number no fact states"


def cited_facts(story: str) -> tuple[int, ...]:
    """Every fact number the narration refers to, ranges expanded.

    Models write "[F1][F2]", "[F1, F2]" and "[F10-F16]" to mean the same
    thing. A check that understood only the first would report defects
    the narration does not have.
    """
    numbers: list[int] = []
    for match in CITATION.finditer(story):
        found = [int(value) for value in CITATION_NUMBERS.findall(match.group(0))]
        if (len(found) == 2 and "-" in match.group(0)) or "to" in match.group(0):
            start, end = min(found), max(found)
            numbers.extend(range(start, end + 1))
        else:
            numbers.extend(found)
    return tuple(numbers)


def _digits(text: str) -> set[str]:
    found: set[str] = set()
    for match in NUMBER.finditer(text):
        digits = re.sub(r"[^\d]", "", match.group(0))
        if len(digits) >= MIN_CHECKED_DIGITS:
            found.add(digits.lstrip("0") or "0")
    return found


def validate_narration(story: str, facts: Sequence[str]) -> tuple[NarrationDefect, ...]:
    """The defects this narration carries, in a fixed order."""
    if not story.strip() or not facts:
        return ()

    defects: list[NarrationDefect] = []
    cited = cited_facts(story)
    if not cited:
        defects.append(NarrationDefect.UNCITED)
    elif any(number < 1 or number > len(facts) for number in cited):
        defects.append(NarrationDefect.UNKNOWN_CITATION)

    stated = _digits(CITATION.sub(" ", story))
    supported = _digits(" ".join(facts))
    if any(number not in supported for number in stated):
        defects.append(NarrationDefect.UNSUPPORTED_NUMBER)
    return tuple(defects)
