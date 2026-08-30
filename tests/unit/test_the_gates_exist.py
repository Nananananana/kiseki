"""The gates CI claims to run are gates that exist.

Every break-and-watch in this repository has injected a *changed* value:
a schema excluded from a wheel, a row deleted from a table, a forbidden
import added. None of them removed the thing a guard was watching -- and
when that was finally tried, deleting the whole `package` job from the
workflow turned nothing red. The gate added to catch packaging mistakes
could be removed without a sound.

The iriguchi session lost seven guards to a single renamed job, one of
them a guard for the job's own existence: written as an absence, it
passed the moment the job it was checking for was gone. So every
assertion here is about **presence**. A missing gate fails; a renamed
gate fails; a workflow that cannot be parsed fails.
"""

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
AGENTS = REPO_ROOT / "AGENTS.md"

JOBS = ("test", "package")
"""`test` runs against the source tree; `package` runs against a built
wheel and is the only one that can see what a wheel does not carry."""

GATES = (
    "pytest",
    "mypy",
    "lint-imports",
    "ruff check",
    "ruff format",
    "tools/check_packaging.py",
)
"""Named literally rather than read from anywhere. A list derived from
the thing under test is empty when the thing is gone, and an empty list
satisfies every check made of it."""

SCRIPTS = (REPO_ROOT / "tools" / "check_packaging.py",)


def workflow() -> dict[str, Any]:
    document: dict[str, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return document


def run_steps() -> list[str]:
    """Every command the workflow runs, across every job."""
    commands: list[str] = []
    for job in workflow()["jobs"].values():
        for step in job.get("steps", []):
            command = step.get("run")
            if isinstance(command, str):
                commands.append(command)
    assert commands, "the workflow runs no commands at all"
    return commands


def test_the_workflow_parses() -> None:
    assert isinstance(workflow().get("jobs"), dict), "ci.yml declares no jobs"


def test_every_job_is_there() -> None:
    jobs = set(workflow()["jobs"])
    missing = [name for name in JOBS if name not in jobs]
    assert not missing, f"jobs missing from ci.yml: {missing}. Present: {sorted(jobs)}"


def test_every_gate_is_run() -> None:
    commands = "\n".join(run_steps())
    missing = [gate for gate in GATES if gate not in commands]
    assert not missing, f"CI no longer runs: {missing}"


def test_every_script_a_gate_runs_exists() -> None:
    """A step invoking a script that is not there fails for the wrong
    reason, and reads as a broken runner rather than a missing gate."""
    missing = [str(path.relative_to(REPO_ROOT)) for path in SCRIPTS if not path.is_file()]
    assert not missing, f"CI runs scripts that do not exist: {missing}"


def test_the_instructions_name_the_same_gates() -> None:
    """AGENTS.md tells a contributor what to run before committing. If
    that list and the workflow drift apart, one of them is lying to
    somebody who cannot tell."""
    instructions = AGENTS.read_text(encoding="utf-8")
    missing = [gate for gate in GATES if gate not in instructions]
    assert not missing, f"AGENTS.md no longer names: {missing}"
