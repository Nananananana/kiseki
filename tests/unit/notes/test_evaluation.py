"""How well the classifier reads, measured rather than asserted."""

import json
from pathlib import Path

from kiseki_notes.evaluation import Expectation, read_expectations, score


def _answers(**pairs: tuple[str, tuple[str, ...]]) -> dict[str, tuple[str, tuple[str, ...]]]:
    return dict(pairs)


def test_a_sensitive_note_read_as_ordinary_is_a_leak() -> None:
    expectations = [Expectation(path="a.md", category="journal")]
    result = score(expectations, {"a.md": ("other", ("moving", "flat"))})
    assert result.leak_rate == 1.0
    assert result.labels_leaked == 2
    assert result.leaks[0].path == "a.md"


def test_an_ordinary_note_read_as_sensitive_is_only_caution() -> None:
    expectations = [Expectation(path="a.md", category="recipe")]
    result = score(expectations, {"a.md": ("health", ())})
    assert result.leak_rate == 0.0
    assert result.over_caution_rate == 1.0
    assert result.labels_leaked == 0


def test_one_sensitive_category_read_as_another_is_not_a_leak() -> None:
    """Both withhold their labels, so nothing was recorded that should not be."""
    expectations = [Expectation(path="a.md", category="journal")]
    result = score(expectations, {"a.md": ("health", ())})
    assert result.leak_rate == 0.0
    assert result.exact == 0


def test_an_acceptable_answer_counts_as_one() -> None:
    expectations = [Expectation(path="a.md", category="reading", acceptable=("study", "note"))]
    result = score(expectations, {"a.md": ("study", ("systems",))})
    assert result.exact == 0
    assert result.allowed == 1


def test_the_rates_are_over_their_own_denominators() -> None:
    expectations = [
        Expectation(path="s1.md", category="journal"),
        Expectation(path="s2.md", category="money"),
        Expectation(path="o1.md", category="work"),
        Expectation(path="o2.md", category="recipe"),
    ]
    result = score(
        expectations,
        {
            "s1.md": ("other", ("a",)),
            "s2.md": ("money", ()),
            "o1.md": ("work", ()),
            "o2.md": ("recipe", ()),
        },
    )
    assert result.leak_rate == 0.5
    assert result.over_caution_rate == 0.0


def test_a_note_nobody_answered_for_is_not_counted() -> None:
    expectations = [
        Expectation(path="a.md", category="work"),
        Expectation(path="b.md", category="work"),
    ]
    result = score(expectations, {"a.md": ("work", ())})
    assert len(result.outcomes) == 1


def test_expectations_are_read_from_the_corpus(tmp_path: Path) -> None:
    path = tmp_path / "expectations.json"
    path.write_text(
        json.dumps(
            {
                "notes": [
                    {"path": "a.md", "category": "journal", "acceptable": []},
                    {"path": "b.md", "category": "reading", "acceptable": ["study"]},
                ]
            }
        ),
        encoding="utf-8",
    )
    expectations = read_expectations(path)
    assert len(expectations) == 2
    assert expectations[0].sensitive
    assert expectations[1].allows("study")
    assert not expectations[1].allows("work")


def test_nothing_measured_is_no_leak() -> None:
    result = score([], {})
    assert result.leak_rate == 0.0
    assert result.over_caution_rate == 0.0
