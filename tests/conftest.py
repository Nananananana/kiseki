import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent the developer's environment variables from leaking into tests."""
    for key in list(os.environ):
        if key.startswith("KISEKI_"):
            monkeypatch.delenv(key, raising=False)
