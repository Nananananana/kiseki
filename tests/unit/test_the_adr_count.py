"""The ADR count is quoted twice, and both copies are checked here.

`AGENTS.md` and `README.md` each say how many ADRs there are, and the
number earns its place: *read the ADRs that cover what you are changing,
there are 84* tells a contributor not to try reading them all. It is
also the only number in either document that changes a reader's
behaviour.

Two copies of one fact is the shape that broke tsumugi, where the same
count read 798 in one document and 741 in another, and the true number
was 1084. **The difference between two disagreeing numbers does not
measure how wrong either of them is**, and copying the larger into both
would have left them 286 short and internally consistent -- wrong more
quietly, having noticed. So neither copy is checked against the other.
Both are checked against the directory.

Counting the files rather than taking the highest number is deliberate.
ADR-0074 was cited by the code for ten commits while its file did not
exist (#305), and a check built on the highest number would have passed
throughout.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
ADRS = REPO_ROOT / "docs" / "adr"
AGENTS = REPO_ROOT / "AGENTS.md"
README = REPO_ROOT / "README.md"

NUMBERED = re.compile(r"^(\d{4})-.+\.md$")


def numbers() -> list[int]:
    found = [
        int(match.group(1))
        for path in ADRS.iterdir()
        if (match := NUMBERED.match(path.name)) is not None
    ]
    assert found, "docs/adr holds no numbered decisions"
    return sorted(found)


def quoted(document: Path, pattern: str) -> int:
    match = re.search(pattern, document.read_text(encoding="utf-8"))
    assert match, f"{document.name} no longer says how many ADRs there are: {pattern}"
    return int(match.group(1))


def test_agents_says_how_many_there_are() -> None:
    assert quoted(AGENTS, r"There are (\d+)\.") == len(numbers())


def test_the_readme_says_how_many_there_are() -> None:
    assert quoted(README, r"docs/adr\) -- (\d+) ADRs") == len(numbers())


def test_every_number_from_the_first_to_the_last_exists() -> None:
    """A gap means a decision was made and its reasoning was not
    written, which happened once and was cited by the code throughout."""
    present = numbers()
    missing = [n for n in range(1, present[-1] + 1) if n not in present]
    assert not missing, f"ADR numbers cited by nothing that exists: {missing}"


def test_no_number_is_used_twice() -> None:
    present = numbers()
    twice = sorted({n for n in present if present.count(n) > 1})
    assert not twice, f"two decisions share a number: {twice}"
