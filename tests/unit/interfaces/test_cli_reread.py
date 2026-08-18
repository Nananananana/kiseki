"""kiseki reread says what a new prompt left behind; --apply clears it."""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqliteCaptionRepository, connect
from kiseki.application.captioning import CAPTION_PROMPT_VERSION
from kiseki.config.paths import resolve_paths
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.photo.observation import PhotoId
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _seed(tmp_path: Path, name: str, version: str | None) -> None:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    SqliteCaptionRepository(connection).save(
        Caption(
            key=CaptionKey.of([PhotoId(f"sha256:{name}")]),
            photo_ids=(PhotoId(f"sha256:{name}"),),
            text="a bowl of ramen",
            model="vl",
            created_at=WHEN,
            prompt_version=version,
        )
    )
    connection.close()


class TestRereadCommand:
    def test_every_stage_reports(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "reread"]) == EXIT_OK
        out = capsys.readouterr().out
        for stage in ("captions", "singles", "subjects", "themes", "screens"):
            assert stage in out
        assert "--apply" in out

    def test_apply_without_a_stage_is_refused(self, tmp_path: Path) -> None:
        assert main(["--data-root", str(tmp_path), "reread", "--apply"]) == EXIT_BAD_INPUT

    def test_apply_clears_only_the_outdated(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path, "aa", "stay-caption/0")
        _seed(tmp_path, "bb", CAPTION_PROMPT_VERSION)
        assert (
            main(["--data-root", str(tmp_path), "reread", "--stage", "captions", "--apply"])
            == EXIT_OK
        )
        assert "cleared 1" in capsys.readouterr().out
        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        connection = connect(paths.db_path)
        remaining = SqliteCaptionRepository(connection).all()
        assert len(remaining) == 1
        assert remaining[0].prompt_version == CAPTION_PROMPT_VERSION
