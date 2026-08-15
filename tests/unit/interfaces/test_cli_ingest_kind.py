"""The ingest command carries the content kind into storage."""

import json
import os
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqlitePhotoRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _run(tmp_path: Path, *arguments: str) -> int:
    return main(["--data-root", str(tmp_path), *arguments])


class TestIngestContentKind:
    def test_the_kind_reaches_storage(self, tmp_path: Path) -> None:
        document = {
            "records": [
                {
                    "id": "sha256:aa11",
                    "captured_at": "2026-06-01T10:00:00+09:00",
                    "location": None,
                    "content_kind": "screenshot",
                }
            ]
        }
        records = tmp_path / "records.json"
        records.write_text(json.dumps(document), encoding="utf-8")

        assert _run(tmp_path, "ingest", str(records)) == EXIT_OK

        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        connection = connect(paths.db_path)
        try:
            stored = SqlitePhotoRepository(connection).all()[0]
        finally:
            connection.close()
        assert stored.content_kind == "screenshot"
