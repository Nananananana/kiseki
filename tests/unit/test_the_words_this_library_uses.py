"""The glossary defines words this library actually uses.

A technical review asked for the domain language to be fixed and found
nothing had written it down. `docs/glossary.md` is that, and this is
what keeps it from becoming a page about a library that used to exist.

**The direction that matters is the second one.** A word missing from
the glossary is an omission somebody can notice by reading. A word
*in* the glossary that the code no longer uses is worse: a contributor
looks it up, finds a confident definition, and builds on a term that
was renamed two versions ago. Documentation that is wrong reads
exactly like documentation that is right.

Checked against `packages/*/src` rather than the whole tree, because
what a contributor relies on is the shipped vocabulary, not a word
that survives in a test name.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
GLOSSARY = REPO_ROOT / "docs" / "glossary.md"
SOURCE = REPO_ROOT / "packages"

TERM = re.compile(r"^\| \*\*(\w+)\*\* \|", re.MULTILINE)

RARE = {
    "grounding": (
        "new in #389 and used in one module, which is where a word "
        "starts. It is in the glossary because the moment/pattern "
        "distinction is the one a reader most needs and least expects."
    ),
    "pattern": (
        "the reader-facing name for what `grounding` builds. Used "
        "sparsely in code and constantly in output, which is the "
        "direction that matters for a glossary."
    ),
}
"""Terms allowed to appear fewer times than `FLOOR`, with why.

Not a way round the check: a term listed here still has to appear in
the source at all. It is a way of saying *this word is young* out
loud, rather than by lowering the floor for everything."""

FLOOR = 10
"""Appearances in shipped source below which a word is not really this
library's vocabulary. Chosen, not measured -- the measured spread runs
from 3 to 508, and anything in double figures is unambiguously in use."""


def defined() -> list[str]:
    terms = TERM.findall(GLOSSARY.read_text(encoding="utf-8"))
    assert terms, "docs/glossary.md defines no terms, so this checks nothing"
    return terms


def appearances(term: str) -> int:
    total = 0
    for path in SOURCE.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        total += len(re.findall(rf"\b{term}", path.read_text(encoding="utf-8"), re.IGNORECASE))
    return total


def test_the_glossary_defines_a_vocabulary() -> None:
    """The population, before it is trusted."""
    assert len(defined()) >= 20, f"only {len(defined())} terms defined"


def test_no_term_is_defined_twice() -> None:
    """Two rows for one word is two definitions, and a reader finds
    whichever comes first."""
    terms = defined()
    assert len(terms) == len(set(terms)), (
        f"defined more than once: {sorted({t for t in terms if terms.count(t) > 1})}"
    )


@pytest.mark.parametrize("term", defined())
def test_every_defined_word_is_a_word_the_code_uses(term: str) -> None:
    """The direction that matters: a confident definition of a word
    that was renamed two versions ago."""
    seen = appearances(term)
    assert seen > 0, (
        f"the glossary defines {term!r} and no shipped source uses it. "
        "Either it was renamed and the glossary did not follow, or it "
        "never existed."
    )
    if term in RARE:
        return
    assert seen >= FLOOR, (
        f"{term!r} appears {seen} times in shipped source, below {FLOOR}. "
        f"Either it is not really this library's vocabulary, or it is new "
        f"-- add it to RARE with the reason, as {sorted(RARE)} are."
    )


def test_every_rare_term_is_actually_defined() -> None:
    """An excuse for a word nobody defines is an excuse for nothing."""
    unknown = sorted(set(RARE) - set(defined()))
    assert not unknown, f"excused here but absent from the glossary: {unknown}"


def test_every_rare_term_says_why() -> None:
    silent = [term for term, reason in RARE.items() if len(reason.split()) < 8]
    assert not silent, f"excused without a reason worth reading: {silent}"


def test_the_four_that_are_confused_are_all_defined() -> None:
    """`stay`, `stop`, `outing`, `anchor` are the spine, and the reason
    the page exists: a reader met all four in one paragraph with
    nothing to separate them."""
    missing = [word for word in ("stay", "stop", "outing", "anchor") if word not in defined()]
    assert not missing, f"the glossary no longer separates: {missing}"
