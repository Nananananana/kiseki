"""Build the packages, install one, and use it from outside the source tree.

Every other check in this repository runs against `uv sync --all-packages`,
which puts the source tree on the path. That makes packaging mistakes
invisible: a schema left out of the wheel, a console script that does not
install, a dependency declared where it should not be. The tests stay green
because they never see a built artefact.

`kiseki-conformance` is the package where that matters most. It exists to be
installed by somebody else -- a producer written in Swift or Kotlin runs
`kiseki-conformance output.json`, and a producer written in Python subclasses
the suite. Both need the schemas that live inside the package, read through
`importlib.resources`. "Installed without its schemas" is close to the only
way this package can fail, and nothing was checking it.

    uv run python tools/check_packaging.py

Runs in CI on both platforms, and takes about half a minute locally.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

IMPORT_NAMES = {
    "kiseki-0": "kiseki",
    "kiseki_conformance-": "kiseki_conformance",
    "kiseki_ingest-": "kiseki_ingest",
    "kiseki_notes-": "kiseki_notes",
    "kiseki_web-": "kiseki_web",
}
"""The distribution name is not the import name. A wheel is addressed
by the first and unpacked to the second, and a check that assumed they
matched would pass on four of these five."""

CONFORMANCE_SCHEMAS = ("photo-record-v1.json", "interest-export-v1.json")
"""Every schema the kit reads at runtime. Absent from the wheel, the package
imports cleanly and fails on first use, in somebody else's program."""

PROBE_TEST = '''\
"""Written by tools/check_packaging.py, run against the installed wheel."""

import json
from pathlib import Path

import pytest
from kiseki_conformance import InterestExportConformance, PhotoRecordConformance


class TestExportFromAWheel(InterestExportConformance):
    @pytest.fixture
    def document(self):
        return json.loads(Path("interest-export.json").read_text(encoding="utf-8"))


class TestPhotoRecordFromAWheel(PhotoRecordConformance):
    @pytest.fixture
    def document(self):
        return json.loads(Path("photo-record.json").read_text(encoding="utf-8"))
'''


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print(f"  $ {' '.join(str(part) for part in command)}")
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def fail(message: str, result: subprocess.CompletedProcess[str] | None = None) -> None:
    print(f"\nFAILED: {message}")
    if result is not None:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
    raise SystemExit(1)


WINDOWS = sys.platform == "win32"


def scripts_dir(venv: Path) -> Path:
    """`Scripts` on Windows, `bin` everywhere else."""
    return venv / ("Scripts" if WINDOWS else "bin")


def build(into: Path) -> list[Path]:
    result = run(["uv", "build", "--all-packages", "--out-dir", str(into)], cwd=REPO_ROOT)
    if result.returncode != 0:
        fail("the packages do not build", result)
    artefacts = sorted(
        path for path in into.iterdir() if path.suffix == ".whl" or path.name.endswith(".tar.gz")
    )
    print(f"  built {len(artefacts)} artefacts")
    return artefacts


def check_metadata(artefacts: list[Path]) -> None:
    """What PyPI itself would say, plus the promise kiseki-core makes."""
    result = run(["uv", "tool", "run", "twine", "check", *[str(p) for p in artefacts]])
    if result.returncode != 0:
        fail("twine check refuses the artefacts", result)

    wheel = one(artefacts, "kiseki-0", ".whl")
    metadata = read_from_wheel(wheel, "METADATA")
    required = [line for line in metadata.splitlines() if line.startswith("Requires-Dist:")]
    unconditional = [line for line in required if ";" not in line]
    if unconditional:
        fail(
            "kiseki-core declares runtime dependencies, and its whole claim is that it "
            f"has none: {unconditional}"
        )
    print("  kiseki declares no unconditional dependency")


def check_schemas_are_carried(artefacts: list[Path]) -> None:
    wheel = one(artefacts, "kiseki_conformance-", ".whl")
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    missing = [
        name for name in CONFORMANCE_SCHEMAS if f"kiseki_conformance/schemas/{name}" not in names
    ]
    if missing:
        fail(f"the conformance wheel carries no {missing}. Installed, it would fail on first use")
    print(f"  the conformance wheel carries {len(CONFORMANCE_SCHEMAS)} schemas")


def check_the_types_are_shipped(artefacts: list[Path]) -> None:
    """Every wheel carries `py.typed`, or its annotations are private.

    PEP 561: without the marker a consumer's type checker skips the
    package entirely, and says so in one line -- the line every
    consumer silences. Measured before this check existed: with that
    line silenced, assigning this kit's `list[str]` to an `int` raised
    **no error at all**. Strict inside, nothing reaching the outside,
    and quietly.

    The kit is the sharpest case, being the one distribution whose
    reason to exist is that somebody else installs it.
    """
    missing = []
    for prefix, package in IMPORT_NAMES.items():
        wheel = one(artefacts, prefix, ".whl")
        with zipfile.ZipFile(wheel) as archive:
            if f"{package}/py.typed" not in set(archive.namelist()):
                missing.append(wheel.name)
    if missing:
        fail(f"wheels shipping annotations nobody can see: {missing}")
    print(f"  {len(IMPORT_NAMES)} wheels carry py.typed")


def one(artefacts: list[Path], prefix: str, suffix: str) -> Path:
    found = [p for p in artefacts if p.name.startswith(prefix) and p.name.endswith(suffix)]
    if len(found) != 1:
        fail(f"expected exactly one {prefix}*{suffix}, found {[p.name for p in found]}")
    return found[0]


def read_from_wheel(wheel: Path, tail: str) -> str:
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.endswith(f".dist-info/{tail}"):
                return archive.read(name).decode("utf-8")
    fail(f"{wheel.name} has no {tail}")
    raise AssertionError("unreachable")


def use_from_outside(artefacts: list[Path], workspace: Path) -> None:
    """Install the wheel and use it where the source tree cannot be seen."""
    venv = workspace / "venv"
    result = run(["uv", "venv", str(venv)])
    if result.returncode != 0:
        fail("the probe environment could not be created", result)
    python = scripts_dir(venv) / ("python.exe" if WINDOWS else "python")

    wheel = one(artefacts, "kiseki_conformance-", ".whl")
    result = run(["uv", "pip", "install", "--python", str(python), str(wheel)])
    if result.returncode != 0:
        fail("the conformance wheel does not install", result)

    probe = workspace / "probe"
    probe.mkdir()
    shutil.copy(
        REPO_ROOT / "tests" / "fixtures" / "interest_export" / "valid_full.json",
        probe / "interest-export.json",
    )
    shutil.copy(
        REPO_ROOT / "tests" / "fixtures" / "photo_record" / "valid_full.json",
        probe / "photo-record.json",
    )
    (probe / "test_from_a_wheel.py").write_text(PROBE_TEST, encoding="utf-8")

    titles = (
        "import json;"
        "from kiseki_conformance import load_export_schema, load_schema;"
        "print(json.dumps(sorted([load_schema()['title'], load_export_schema()['title']])))"
    )
    result = run([str(python), "-c", titles], cwd=probe)
    if result.returncode != 0:
        fail("the installed package cannot read its own schemas", result)
    print(f"  schemas read from the installed package: {result.stdout.strip()}")

    name = "kiseki-conformance.exe" if WINDOWS else "kiseki-conformance"
    cli = scripts_dir(venv) / name
    if not cli.exists():
        fail(f"the console script was not installed at {cli}")
    for document in ("interest-export.json", "photo-record.json"):
        result = run([str(cli), document], cwd=probe)
        if result.returncode != 0:
            fail(f"the installed command line refuses {document}", result)
        print(f"  {result.stdout.strip()}")

    result = run([str(python), "-m", "pytest", "-q", "test_from_a_wheel.py"], cwd=probe)
    if result.returncode != 0:
        fail("the suites do not pass when subclassed from an installed wheel", result)
    print(f"  {result.stdout.strip().splitlines()[-1]}")


def main() -> int:
    print(json.dumps({"repository": str(REPO_ROOT)}))
    with tempfile.TemporaryDirectory(prefix="kiseki-packaging-") as raw:
        workspace = Path(raw)
        print("\nbuilding")
        artefacts = build(workspace / "dist")
        print("\nchecking metadata")
        check_metadata(artefacts)
        print("\nchecking what the wheel carries")
        check_schemas_are_carried(artefacts)
        check_the_types_are_shipped(artefacts)
        print("\nusing it from outside the source tree")
        use_from_outside(artefacts, workspace)
    print("\nthe packages build, install, and work where the source tree is not")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
