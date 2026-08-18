"""kiseki retry reports recoverable refusals; --apply takes them back."""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import SqliteSingleCaptionRepository, connect
from kiseki.config.paths import resolve_paths
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.photo.observation import PhotoId
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _seed(tmp_path: Path, name: str, refused: str) -> None:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    SqliteSingleCaptionRepository(connection).save(
        SingleCaption(
            photo_id=PhotoId(f"sha256:{name}"),
            text="",
            model="",
            created_at=WHEN,
            refused=refused,
        )
    )
    connection.close()


class TestRetryCommand:
    def test_every_stage_reports(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "retry"]) == EXIT_OK
        out = capsys.readouterr().out
        for stage in ("captions", "singles", "subjects", "screens"):
            assert stage in out
        assert "--apply" in out

    def test_apply_without_a_stage_is_refused(self, tmp_path: Path) -> None:
        assert main(["--data-root", str(tmp_path), "retry", "--apply"]) == EXIT_BAD_INPUT

    def test_apply_takes_back_only_the_recoverable(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path, "aa", "no thumbnail at 2026/08/aa.jpg")
        _seed(tmp_path, "bb", "the model declined to describe this")
        assert (
            main(["--data-root", str(tmp_path), "retry", "--stage", "singles", "--apply"])
            == EXIT_OK
        )
        assert "took back 1" in capsys.readouterr().out
        paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
        connection = connect(paths.db_path)
        remaining = SqliteSingleCaptionRepository(connection).all()
        assert len(remaining) == 1
        assert remaining[0].refused == "the model declined to describe this"
