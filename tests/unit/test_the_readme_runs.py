"""Every command the README tells a reader to type is a command.

`test_documented_commands.py` holds `docs/cli.md` and `AGENTS.md` to
the parser. It does not hold the README, and the README is the one a
stranger reads first.

Found by making the mistake. Restructuring the front page, two
commands went into the quick start that exist on a branch and not on
`main` -- `kiseki cost` and `kiseki map` -- and the whole suite stayed
green. A reader following the quick start would have got
`invalid choice`, from the only page they had read.

`kiseki-ingest` was wrong in a quieter way: the flags were invented
from memory of what such a tool takes, and it actually requires
`--owner` and `--default-offset` and takes its output as a positional.
Nothing would have said so until somebody tried it.

So: every `kiseki` and `kiseki-ingest` line in the README is checked
against the parser that would run it. Not executed -- these touch a
photo library -- but the verb has to exist and the flags have to parse.
"""

import argparse
import re
import shlex
from pathlib import Path

import pytest
from kiseki.interfaces.cli import build_parser

REPO_ROOT = Path(__file__).parents[2]
README = REPO_ROOT / "README.md"

INVOCATION = re.compile(r"^\s*(?:uv run |\$ )?(kiseki(?:-ingest)?)\s+(.*)$")

PLACEHOLDERS = ("...", "<", "lat,lon")
"""Lines written to show a shape rather than to be typed. A line
holding one of these is a sentence about a command, not a command."""


def blocks() -> list[str]:
    text = README.read_text(encoding="utf-8")
    found = re.findall(r"```(?:bash|text)\n(.*?)```", text, re.DOTALL)
    assert found, "the README holds no command blocks, so this checks nothing"
    return found


def invocations() -> list[tuple[str, str]]:
    found = []
    for block in blocks():
        for line in block.splitlines():
            line = line.split("#")[0].strip()
            if not line or any(mark in line for mark in PLACEHOLDERS):
                continue
            match = INVOCATION.match(line)
            if match:
                found.append((match.group(1), match.group(2)))
    assert found, "no kiseki invocations found in the README, so this checks nothing"
    return found


def verbs() -> set[str]:
    for action in build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise AssertionError("the parser has no subcommands")


def test_the_readme_tells_a_reader_to_type_something() -> None:
    """The population, asserted before it is trusted."""
    assert len(invocations()) >= 5, f"only {len(invocations())} invocations found"


def test_every_kiseki_command_in_the_readme_exists() -> None:
    """The mistake this file was written for: `kiseki cost` and
    `kiseki map` are real commands on branches, and were not on the
    page's own branch."""
    known = verbs()
    missing = []
    for program, rest in invocations():
        if program != "kiseki":
            continue
        words = [word for word in shlex.split(rest) if not word.startswith("-")]
        if words and words[0] not in known:
            missing.append(words[0])
    assert not missing, (
        f"the README tells a reader to run commands that do not exist: {sorted(set(missing))}. "
        f"Known: {', '.join(sorted(known))}"
    )


def test_every_kiseki_invocation_parses() -> None:
    """The flags too, not only the verb. A `--out` that is really a
    positional is a quick start that fails on line one."""
    refused = []
    for program, rest in invocations():
        if program != "kiseki":
            continue
        try:
            build_parser().parse_args(shlex.split(rest))
        except SystemExit:
            refused.append(f"kiseki {rest}")
    assert not refused, f"the README's own commands do not parse: {refused}"


def test_the_ingest_invocation_parses() -> None:
    """`kiseki-ingest` is a separate program with its own parser, and
    the README's line for it was invented from memory once."""
    from kiseki_ingest.cli import _parser as ingest_parser

    refused = []
    for program, rest in invocations():
        if program != "kiseki-ingest":
            continue
        try:
            ingest_parser().parse_args(shlex.split(rest))
        except SystemExit:
            refused.append(f"kiseki-ingest {rest}")
    assert not refused, f"the README's ingest line does not parse: {refused}"


@pytest.mark.parametrize("promised", ["build", "report", "privacy"])
def test_a_command_promised_to_need_no_model_is_named(promised: str) -> None:
    """The README says these work without a model. That claim sends a
    reader without Ollama to a specific list, so the list has to hold
    commands that exist."""
    assert promised in verbs()
