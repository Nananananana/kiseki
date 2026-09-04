"""The current-state documents list the commands that exist, and only those.

`docs/README.md` says that a current-state document disagreeing with the
code is a defect rather than a difference of opinion. Three commands --
`activity`, `notes` and `llm` -- shipped and were never written down, and
nothing noticed for a version and a half. A description drifts silently;
this turns the drift red.
"""

import re
from argparse import _SubParsersAction
from pathlib import Path

from kiseki.interfaces.cli import build_parser

REPO_ROOT = Path(__file__).parents[2]
CLI_DOC = REPO_ROOT / "docs" / "cli.md"
AGENTS = REPO_ROOT / "AGENTS.md"


def registered_commands() -> set[str]:
    """Every command the parser actually offers."""
    for action in build_parser()._actions:
        if isinstance(action, _SubParsersAction):
            return set(action.choices)
    raise AssertionError("the parser has no subcommands")


def documented_in_cli_reference() -> set[str]:
    """The names in the command table of docs/cli.md."""
    rows = re.findall(r"^\| `([a-z-]+)` \|", CLI_DOC.read_text(encoding="utf-8"), re.MULTILINE)
    assert rows, (
        "no command rows found in docs/cli.md, which means the table's shape "
        "changed rather than that it documents nothing. Without this, "
        "test_the_cli_reference_invents_no_command passes by subtracting from "
        "an empty set -- measured: 1 failed, 4 passed, where the one failure "
        "was its partner rather than itself."
    )
    return set(rows)


def listed_in_agents() -> tuple[set[str], int]:
    """The names in the Commands bullet of AGENTS.md, and the count it claims."""
    text = AGENTS.read_text(encoding="utf-8")
    match = re.search(r"- Commands \((\d+)\):(.*?)(?=\n- )", text, re.DOTALL)
    assert match, "AGENTS.md has no '- Commands (n):' bullet"
    return set(re.findall(r"`([a-z-]+)`", match.group(2))), int(match.group(1))


def test_agents_lists_the_commands_once() -> None:
    """A second bullet is a second list, and only the first is checked.

    AGENTS.md carried two `- Commands (n):` bullets at once. The
    regexes below stop at the first, so the second was dead text that
    nothing held to anything -- it had drifted to a different count
    and a different set of names, and every test here passed.

    Two copies of one fact is the shape that broke tsumugi, and the
    answer there was the same: do not check one copy against the
    other, check that there is one copy.
    """
    bullets = [
        line
        for line in AGENTS.read_text(encoding="utf-8").splitlines()
        if line.startswith("- Commands (")
    ]
    assert len(bullets) == 1, (
        f"AGENTS.md has {len(bullets)} command bullets. Everything below reads the "
        f"first, so the rest are unchecked: {bullets}"
    )


def test_every_command_is_in_the_cli_reference() -> None:
    missing = registered_commands() - documented_in_cli_reference()
    assert not missing, f"commands missing from docs/cli.md: {sorted(missing)}"


def test_the_cli_reference_invents_no_command() -> None:
    invented = documented_in_cli_reference() - registered_commands()
    assert not invented, f"docs/cli.md documents commands that do not exist: {sorted(invented)}"


def test_every_command_is_listed_in_agents() -> None:
    listed, _count = listed_in_agents()
    missing = registered_commands() - listed
    assert not missing, f"commands missing from AGENTS.md: {sorted(missing)}"


def test_agents_lists_no_command_that_does_not_exist() -> None:
    listed, _count = listed_in_agents()
    invented = listed - registered_commands()
    assert not invented, f"AGENTS.md lists commands that do not exist: {sorted(invented)}"


def test_the_count_in_agents_is_the_count() -> None:
    listed, count = listed_in_agents()
    assert count == len(listed) == len(registered_commands())
