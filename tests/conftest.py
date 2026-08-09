import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """開発者の環境変数がテストへ漏れるのを防ぐ。"""
    for key in list(os.environ):
        if key.startswith("KISEKI_"):
            monkeypatch.delenv(key, raising=False)