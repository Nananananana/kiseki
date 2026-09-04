"""Every shipped source file is in the repository.

A test suite runs against the working tree, so a file that exists on
disk and is not in git passes every check there is -- and is absent
from the clone anybody else makes.

Found by making it happen. `.gitignore` carried

    records/

among the rules that keep the owner's personal data out. A gitignore
pattern with no leading slash matches a directory of that name **at
any depth**, so it silently swallowed

    packages/kiseki-core/src/kiseki/adapters/records/

which was the entire subject of the pull request that added it. 1830
tests passed. `git status` said nothing, because an ignored file is
not untracked, it is invisible. The branch pushed, the pull request
opened, and the module that made it work was not in it.

This repository already knows this failure -- four merged pull
requests once delivered 539 lines that were not on `main`, and
`AGENTS.md` gained a checkpoint that reads the repository rather than
the badge. That checkpoint would have caught this too, and was not
run.

So this is the machine version: every Python file under a package's
`src` is tracked, and no source path is ignored. It costs one `git`
call and it fails loudly at the moment the mistake is made rather than
at the moment somebody clones.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
PACKAGES = REPO_ROOT / "packages"


def shipped_files() -> list[Path]:
    """Every Python file that a wheel would carry."""
    found = [
        path
        for path in PACKAGES.rglob("*.py")
        if "__pycache__" not in path.parts and "src" in path.parts
    ]
    assert found, "no shipped Python found, so this test is looking in the wrong place"
    return found


def tracked() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "packages"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"git ls-files failed: {result.stderr}"
    paths = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    assert paths, "git tracks nothing under packages/, which cannot be right"
    return paths


def as_repo_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def test_every_shipped_file_is_tracked() -> None:
    """The one that would have caught it."""
    known = tracked()
    missing = sorted(
        as_repo_path(path) for path in shipped_files() if as_repo_path(path) not in known
    )
    assert not missing, (
        f"these are on disk and not in the repository: {missing}. "
        "Every check here passes because they exist locally; a clone would not have them. "
        "Check .gitignore -- a pattern with no leading slash matches at any depth."
    )


def test_no_shipped_file_is_ignored() -> None:
    """The same question asked of git rather than of the index, so a
    file that is ignored *and* has never been added is still caught."""
    paths = [as_repo_path(path) for path in shipped_files()]
    result = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        cwd=REPO_ROOT,
        input="\n".join(paths),
        capture_output=True,
        text=True,
        check=False,
    )
    # exit 0 means at least one path matched an ignore rule
    ignored = sorted(line.strip() for line in result.stdout.splitlines() if line.strip())
    assert not ignored, (
        f".gitignore excludes shipped source: {ignored}. "
        "A pattern with no leading slash matches a directory of that name at any depth."
    )


def test_the_check_can_see_a_file_that_is_not_there() -> None:
    """The check itself, checked. A path git has never heard of has to
    come back as missing, or the comparison above proves nothing."""
    assert "packages/kiseki-core/src/kiseki/not_a_real_module.py" not in tracked()
