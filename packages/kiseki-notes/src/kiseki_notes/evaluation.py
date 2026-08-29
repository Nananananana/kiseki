"""How well the classifier reads, measured rather than asserted.

One number would hide the thing that matters. The classifier has two
errors and they are not the same error:

    a sensitive note read as ordinary   -- its labels are recorded
    an ordinary note read as sensitive  -- the record is thinner

The first is a leak. The second costs coverage. A single accuracy
figure moves the same amount for either, which is why there are three
figures here and the leak is the headline.

The numbers are a floor to hold, not a claim about anybody's notes:
two dozen invented files say nothing about a real folder. What they do
is turn a prompt change from an opinion into a measurement -- the
posture ADR-0069 takes about the export and ADR-0071 about a
comparison. See ADR-0077.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

SENSITIVE = frozenset({"journal", "health", "money", "people", "credential"})


@dataclass(frozen=True)
class Expectation:
    """What one note should be read as, and what else would be fair."""

    path: str
    category: str
    acceptable: tuple[str, ...] = ()

    @property
    def sensitive(self) -> bool:
        return self.category in SENSITIVE

    def allows(self, answer: str) -> bool:
        return answer == self.category or answer in self.acceptable


@dataclass(frozen=True)
class Outcome:
    """What the classifier made of one note, beside what was expected."""

    path: str
    expected: str
    answered: str
    labels: tuple[str, ...]
    acceptable: bool

    @property
    def leaked(self) -> bool:
        """A sensitive note read as ordinary. Its labels were recorded."""
        return self.expected in SENSITIVE and self.answered not in SENSITIVE

    @property
    def over_cautious(self) -> bool:
        return self.expected not in SENSITIVE and self.answered in SENSITIVE


@dataclass
class Score:
    """The three figures, and the rows behind them."""

    outcomes: list[Outcome] = field(default_factory=list)

    @property
    def sensitive(self) -> list[Outcome]:
        return [outcome for outcome in self.outcomes if outcome.expected in SENSITIVE]

    @property
    def ordinary(self) -> list[Outcome]:
        return [outcome for outcome in self.outcomes if outcome.expected not in SENSITIVE]

    @property
    def leaks(self) -> list[Outcome]:
        return [outcome for outcome in self.outcomes if outcome.leaked]

    @property
    def over_cautions(self) -> list[Outcome]:
        return [outcome for outcome in self.outcomes if outcome.over_cautious]

    @property
    def leak_rate(self) -> float:
        return len(self.leaks) / len(self.sensitive) if self.sensitive else 0.0

    @property
    def over_caution_rate(self) -> float:
        return len(self.over_cautions) / len(self.ordinary) if self.ordinary else 0.0

    @property
    def exact(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.answered == outcome.expected)

    @property
    def allowed(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.acceptable)

    @property
    def labels_leaked(self) -> int:
        """How many labels were recorded that should never have been."""
        return sum(len(outcome.labels) for outcome in self.leaks)


def read_expectations(path: Path) -> tuple[Expectation, ...]:
    """The answers, from the file that ships with a corpus."""
    document = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        Expectation(
            path=str(entry["path"]),
            category=str(entry["category"]),
            acceptable=tuple(entry.get("acceptable", [])),
        )
        for entry in document["notes"]
    )


def score(
    expectations: Sequence[Expectation],
    answers: dict[str, tuple[str, tuple[str, ...]]],
) -> Score:
    """Compare what was expected with what came back."""
    result = Score()
    for expectation in expectations:
        if expectation.path not in answers:
            continue
        answered, labels = answers[expectation.path]
        result.outcomes.append(
            Outcome(
                path=expectation.path,
                expected=expectation.category,
                answered=answered,
                labels=labels,
                acceptable=expectation.allows(answered),
            )
        )
    return result
