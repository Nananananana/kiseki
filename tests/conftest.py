import importlib.util
import os

import pytest

WORKSPACE_PACKAGES = (
    "kiseki",
    "kiseki_ingest",
    "kiseki_notes",
    "kiseki_web",
    "kiseki_conformance",
)
"""Every distribution this workspace builds, by import name.

`uv add` and `uv add --dev` re-sync **without** `--all-packages`, which
uninstalls all five. Every test then fails with

    ModuleNotFoundError: No module named 'kiseki'

which reads as a broken test rather than a broken environment, and a
whole afternoon was spent on the far end of that: a mutation-testing
run reported a perfect score because every one of its test commands
was failing this way, and the tool counts a failing command as a
killed mutant. So the collection says what happened instead.
"""


def pytest_configure() -> None:
    """`pytest_configure`, and not `pytest_collection_modifyitems`.

    Written there first: raising `pytest.UsageError` during collection
    is **swallowed**, and the run ends with `no tests ran` and exit 0.
    A guard that turns a broken environment into a silent green is the
    failure it exists to prevent, arriving one layer up.
    """
    missing = [name for name in WORKSPACE_PACKAGES if importlib.util.find_spec(name) is None]
    if missing:
        raise pytest.UsageError(
            f"the workspace packages {missing} are not installed, so these tests cannot "
            "import what they are testing. This is the environment and not the code: "
            "`uv add` re-syncs without --all-packages. Run `uv sync --all-packages`."
        )


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent the developer's environment variables from leaking into tests."""
    for key in list(os.environ):
        if key.startswith("KISEKI_"):
            monkeypatch.delenv(key, raising=False)
