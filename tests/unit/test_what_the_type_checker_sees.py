"""Every directory of Python is type-checked, or named as not.

`uv run mypy packages` was the whole of it. Measured against the tree:
401 Python files, 167 under `packages/`, so **234 unchecked** -- the
largest such count of the six sibling libraries (#355).

Most of that is `tests/`, and most projects do not check their tests.
But `tools/` is not tests. One file in it is a CI gate, and the first
run of the type checker over the three files found a real defect that
had been there since #15: `tools/journeys.py` called `.outings` on a
value that stopped being an object and became a tuple, so the tool
raised `AttributeError` on any document with a photograph in it. Two
years of nobody running it, and nothing to say so.

That is the shape the siblings found too -- iriguchi, widening theirs,
found eight errors of which the two real ones were a corpus generator
and a file whose only job was putting numbers into a document; tsumugi
found eleven, all in measurement scripts. **The unchecked files are
the ones that write things other people read.**

So: a directory of Python is a decision. Check it, or say here why
not. Nothing about this can rot quietly, because both lists below are
checked against the workflow and the tree.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
AGENTS = REPO_ROOT / "AGENTS.md"

CHECKED = ("packages", "tools")
"""Named in the mypy invocation, in CI and in AGENTS.md both."""

NOT_CHECKED = {
    "tests": (
        "Measured, not assumed: 443 errors across 231 files, of which "
        "366 are `no-untyped-def` and `no-untyped-call` -- fixtures and "
        "helpers, whose only caller is pytest. The 34 `arg-type` errors "
        "were read one at a time, because those are where a defect "
        "would be. 25 are a fake narrower than the protocol it stands "
        "in for, which is what a fake is. The other 9 are three sites: "
        "`dict` is invariant in its value type, so a "
        "`dict[str, tuple[float, float]]` is not a "
        "`dict[str, tuple[float, ...]]`; a `**kwargs` splat of a "
        "`dict[str, object]` cannot be narrowed; and one test helper "
        "narrows the first of two optional arguments and not the "
        "second. **Not one of the 443 is a defect in shipped code.** "
        "That is the measurement the decision rests on -- annotating "
        "the suite would buy noise on every line that fakes something, "
        "which in a suite this size is most of the interesting lines. "
        "Revisit if a test ever ships."
    ),
}
"""Why each one is absent. A directory here has been looked at, which
is the whole difference between this answer and no answer."""


def python_directories() -> set[str]:
    """Top-level directories of the repository that hold Python."""
    found = {
        path.relative_to(REPO_ROOT).parts[0]
        for path in REPO_ROOT.rglob("*.py")
        if ".venv" not in path.parts and "__pycache__" not in path.parts
    }
    assert found, "no Python in this repository, which means this is looking in the wrong place"
    return {name for name in found if (REPO_ROOT / name).is_dir()}


def mypy_invocations() -> list[str]:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    found = [
        command
        for job in document["jobs"].values()
        for step in job.get("steps", [])
        if isinstance(command := step.get("run"), str) and "mypy" in command
    ]
    assert found, "the workflow no longer runs mypy at all"
    return found


def test_every_directory_of_python_is_decided() -> None:
    undecided = python_directories() - set(CHECKED) - set(NOT_CHECKED)
    assert not undecided, (
        f"directories of Python that nothing has decided about: {sorted(undecided)}. "
        "Type-check them, or say here why not."
    )


def test_nothing_is_named_that_does_not_exist() -> None:
    invented = (set(CHECKED) | set(NOT_CHECKED)) - python_directories()
    assert not invented, f"named here but holding no Python: {sorted(invented)}"


def test_no_directory_is_both_checked_and_excused() -> None:
    assert not set(CHECKED) & set(NOT_CHECKED)


def test_every_excuse_says_something() -> None:
    """A blank reason is a directory nobody looked at, which is the one
    answer #355 asked not to be left with."""
    silent = [name for name, reason in NOT_CHECKED.items() if len(reason.split()) < 20]
    assert not silent, f"excused without a reason worth reading: {silent}"


def test_ci_checks_every_directory_it_says_it_checks() -> None:
    commands = "\n".join(mypy_invocations())
    missing = [name for name in CHECKED if name not in commands]
    assert not missing, f"CI runs mypy without: {missing}. Ran: {mypy_invocations()}"


def test_the_instructions_name_the_same_directories() -> None:
    """A contributor runs what AGENTS.md says. If that and the workflow
    disagree, the local run is green and the push is red."""
    for command in mypy_invocations():
        assert command.strip() in AGENTS.read_text(encoding="utf-8"), (
            f"AGENTS.md does not tell a contributor to run `{command.strip()}`"
        )
