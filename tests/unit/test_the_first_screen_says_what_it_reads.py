"""The README's first screen names every kind of evidence this reads.

Measured, not supposed. An outside reader was asked what each of the
six sibling libraries does, and understood this one as:

    photos -> EXIF -> inference -> timeline

Two of those four are wrong. This library does not read EXIF -- a
producer does, and writes `PhotoRecord v1` -- and what comes out is
not a timeline but an interpretation of a person. The first word is
wrong too, though less obviously: **photographs are one of four input
contracts**, and the other three landed in v0.10 and v0.11.

The reader was not being careless. The repository's own description
says *your photo history*, and the README's opening sentence is the
same sentence. **They read it correctly and it was out of date.**

So the check is not on prose quality, which nothing can check. It is
on a fact: every input contract that has a document in `docs/` is
named on the first screen, and appears in the diagram that claims to
show how this works. A fifth contract that lands and is not mentioned
fails here, which is what happened silently to the third and fourth.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
README = REPO_ROOT / "README.md"
RECORDS = REPO_ROOT / "docs" / "records.md"

FIRST_SCREEN = 60
"""Lines. Not a design opinion -- the point of the whole check is that
a fact placed four scrolls down is a fact the reader who needed it did
not reach."""

CONTRACT = re.compile(r"\[(\w+Record v\d+)\]\((\w[\w-]*\.md)\)")


def contracts() -> dict[str, str]:
    """The input contracts, from the table that already lists them."""
    found = dict(CONTRACT.findall(RECORDS.read_text(encoding="utf-8")))
    assert len(found) >= 2, (
        f"docs/records.md no longer lists the input contracts: {found}. "
        "This check reads that table rather than a list of its own."
    )
    return found


def what_it_reads(contract: str) -> str:
    """`PhotoRecord v1` -> `photo`. The word a reader would look for."""
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", contract.split()[0]).split()[0].lower()


def first_screen() -> str:
    return "\n".join(README.read_text(encoding="utf-8").splitlines()[:FIRST_SCREEN]).lower()


def test_the_first_screen_names_every_kind_of_evidence() -> None:
    missing = [
        f"{contract} ({what_it_reads(contract)})"
        for contract in contracts()
        if what_it_reads(contract) not in first_screen()
    ]
    assert not missing, (
        f"the README's first {FIRST_SCREEN} lines do not say this reads: {missing}. "
        "An outside reader understood this library as photographs alone, "
        "because the opening sentence said so."
    )


def test_the_diagram_shows_every_kind_of_evidence() -> None:
    """`How it works` is where a reader goes when the opening interested
    them. A diagram showing one source of four is a second telling of
    the same wrong thing, in the place that looks most authoritative."""
    text = README.read_text(encoding="utf-8")
    diagram = text[text.index("## How it works") :].split("```")[1].lower()
    missing = [
        what_it_reads(contract)
        for contract in contracts()
        if what_it_reads(contract) not in diagram
    ]
    assert not missing, f"the How it works diagram shows no {missing}"


def test_the_contracts_it_names_have_documents() -> None:
    """A contract named in the table whose document is gone would make
    every check above pass against a promise nobody kept."""
    missing = [name for name, page in contracts().items() if not (REPO_ROOT / "docs" / page).is_file()]
    assert not missing, f"docs/records.md links to contracts with no document: {missing}"
