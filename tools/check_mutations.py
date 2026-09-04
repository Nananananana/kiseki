"""Change the code on purpose, and see whether the tests notice.

Every other check in this repository asks *do the tests pass*. This one
asks the question underneath: **would they fail if the code were
wrong.** Today's other work is the reason it exists -- three separate
checks were found passing on populations that could not have failed
them, and no amount of running the suite would have said so.

    uv run python tools/check_mutations.py            # every target
    uv run python tools/check_mutations.py stops      # one of them

A run takes minutes per target, so this is not in CI. It is the
instrument you reach for when you want to know whether a module's
tests are worth their green.

**The control is not optional, and this tool will not print a score
without one.** The first five sessions run by hand reported a perfect
0 survivors everywhere -- including for a module deliberately paired
with tests that cannot possibly detect it. The cause was that
`uv add --dev` had re-synced the environment without `--all-packages`,
so every test command failed with `ModuleNotFoundError` and
**cosmic-ray counts a failing test command as a killed mutant**. A
perfect score meant the instrument was not running at all.

So each run is paired with the same module measured against unrelated
tests. That pairing has to come out near 100% survivors, or the score
beside it means nothing and is refused rather than printed.
"""

import argparse
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CONTROL_TESTS = "tests/unit/domain/note/test_reading.py"
"""Tests that touch no geometry, no clustering and no storage. Paired
with a target they cannot reach, so nearly every mutant must survive."""

CONTROL_FLOOR = 0.9
"""Below this share of survivors the control has not behaved like a
control, and whatever the real run said is not evidence."""


@dataclass(frozen=True)
class Target:
    name: str
    module: str
    tests: str


TARGETS = (
    Target(
        "stops",
        "packages/kiseki-core/src/kiseki/domain/services/stop_extraction.py",
        "tests/unit/domain/test_stop_extraction.py "
        "tests/unit/domain/test_a_value_exactly_on_a_threshold.py",
    ),
    Target(
        "outings",
        "packages/kiseki-core/src/kiseki/domain/services/outing_assembly.py",
        "tests/unit/domain/test_outing_assembly.py",
    ),
    Target(
        "anchors",
        "packages/kiseki-core/src/kiseki/domain/services/anchor_estimation.py",
        "tests/unit/domain/test_anchor_estimation.py",
    ),
)
"""The three derivations a journey is made of. Named rather than
globbed: a target list built by walking the tree is a target list that
silently covers nothing the day the walk stops matching."""

BY_NAME = {target.name: target for target in TARGETS}

SESSION = """\
[cosmic-ray]
module-path = "{module}"
timeout = 60.0
excluded-modules = []
test-command = "uv run pytest -x -q {tests}"

[cosmic-ray.distributor]
name = "local"
"""


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=REPO_ROOT, capture_output=True, text=True, check=False, encoding="utf-8"
    )


def fail(message: str) -> None:
    print(f"\nFAILED: {message}")
    raise SystemExit(1)


def session(workspace: Path, name: str, module: str, tests: str) -> tuple[int, int]:
    """Plan and run one session. Returns (mutants, survivors)."""
    configuration = workspace / f"{name}.toml"
    database = workspace / f"{name}.sqlite"
    configuration.write_text(SESSION.format(module=module, tests=tests), encoding="utf-8")

    planned = run(["uv", "run", "cosmic-ray", "init", str(configuration), str(database)])
    if planned.returncode != 0:
        fail(f"cosmic-ray could not plan {name}: {planned.stderr.strip()}")
    executed = run(["uv", "run", "cosmic-ray", "exec", str(configuration), str(database)])
    if executed.returncode != 0:
        fail(f"cosmic-ray could not run {name}: {executed.stderr.strip()}")

    connection = sqlite3.connect(database)
    try:
        mutants = connection.execute("SELECT count(*) FROM mutation_specs").fetchone()[0]
        outcomes = [row[0] for row in connection.execute("SELECT test_outcome FROM work_results")]
        survivors = sum(1 for outcome in outcomes if str(outcome).upper() == "SURVIVED")
        if outcomes and not any(str(o).upper() in {"SURVIVED", "KILLED"} for o in outcomes):
            fail(f"{name}: cosmic-ray reported outcomes this tool does not know: {set(outcomes)}")
    finally:
        connection.close()
    if mutants == 0:
        fail(f"{name}: no mutants were planned, so nothing was measured")
    return mutants, survivors


def check(target: Target, workspace: Path) -> None:
    print(f"\n{target.name}  ({target.module})")

    print("  control  -- the same module against tests that cannot reach it")
    mutants, survivors = session(workspace, f"{target.name}-control", target.module, CONTROL_TESTS)
    share = survivors / mutants
    print(f"    {survivors} of {mutants} survived  ({share:.0%})")
    if share < CONTROL_FLOOR:
        fail(
            f"{target.name}: the control killed {mutants - survivors} of {mutants} mutants with "
            f"tests that cannot reach the module. The harness is not doing what it says -- "
            "a failing test command counts as a killed mutant, so check that "
            "`uv run pytest` works (try `uv sync --all-packages`) before reading any score."
        )

    print("  measured -- the module against its own tests")
    mutants, survivors = session(workspace, target.name, target.module, target.tests)
    print(f"    {survivors} of {mutants} survived  ({survivors / mutants:.0%})")
    print(f"    score {1 - survivors / mutants:.1%}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", nargs="?", choices=sorted(BY_NAME), default=None)
    arguments = parser.parse_args()

    ready = run(["uv", "run", "python", "-c", "import kiseki"])
    if ready.returncode != 0:
        fail(
            "the workspace packages are not importable, so every test command would fail "
            "and every mutant would be reported killed. Run `uv sync --all-packages`."
        )

    targets = [BY_NAME[arguments.target]] if arguments.target else list(TARGETS)
    with tempfile.TemporaryDirectory(prefix="kiseki-mutations-") as raw:
        workspace = Path(raw)
        for target in targets:
            check(target, workspace)
    print("\nevery score above was printed beside a control that behaved like one")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
