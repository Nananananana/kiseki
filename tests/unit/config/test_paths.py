"""Specification for path resolution.

Nothing in this project has a hardcoded absolute path, including the defaults.
Where a person keeps their photographs is theirs to decide, and the library has
to work without being told.
"""

from pathlib import Path

import pytest

from kiseki.config.paths import StoragePaths, resolve_paths


class TestDefaults:
    def test_falls_back_to_a_directory_in_the_home_folder(self) -> None:
        assert resolve_paths().data_root == Path.home() / ".kiseki"

    def test_derives_everything_from_the_root(self) -> None:
        paths = StoragePaths.derive(Path("/data"))
        assert paths.records_dir == Path("/data/records")
        assert paths.thumbs_dir == Path("/data/thumbs")
        assert paths.cache_dir == Path("/data/cache")

    def test_the_database_sits_under_the_root_too(self) -> None:
        assert StoragePaths.derive(Path("/data")).db_path == Path("/data/db/kiseki.sqlite3")


class TestOverrides:
    def test_an_individual_path_can_be_moved(self) -> None:
        """Bulk storage and fast storage are often different drives."""
        paths = StoragePaths.derive(
            Path("/bulk"), {"db_path": Path("/fast/kiseki.sqlite3")}
        )
        assert paths.db_path == Path("/fast/kiseki.sqlite3")

    def test_the_others_still_follow_the_root(self) -> None:
        paths = StoragePaths.derive(
            Path("/bulk"), {"db_path": Path("/fast/kiseki.sqlite3")}
        )
        assert paths.thumbs_dir == Path("/bulk/thumbs")


class TestPrecedence:
    def test_an_environment_variable_sets_the_root(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KISEKI_DATA_ROOT", "/from/env")
        assert resolve_paths().data_root == Path("/from/env")

    def test_an_environment_variable_sets_an_individual_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KISEKI_DATA_ROOT", "/from/env")
        monkeypatch.setenv("KISEKI_DB_PATH", "/fast/kiseki.sqlite3")
        paths = resolve_paths()
        assert paths.db_path == Path("/fast/kiseki.sqlite3")
        assert paths.thumbs_dir == Path("/from/env/thumbs")

    def test_the_command_line_wins_over_the_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KISEKI_DATA_ROOT", "/from/env")
        assert resolve_paths({"data_root": "/from/cli"}).data_root == Path("/from/cli")

    def test_an_empty_command_line_value_is_not_an_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unset argparse option must not erase a configured value."""
        monkeypatch.setenv("KISEKI_DATA_ROOT", "/from/env")
        assert resolve_paths({"data_root": ""}).data_root == Path("/from/env")

    def test_a_dotenv_file_is_read(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("KISEKI_DATA_ROOT=/from/dotenv\n", encoding="utf-8")
        assert resolve_paths(dotenv=tmp_path / ".env").data_root == Path("/from/dotenv")

    def test_the_environment_wins_over_a_dotenv_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / ".env").write_text("KISEKI_DATA_ROOT=/from/dotenv\n", encoding="utf-8")
        monkeypatch.setenv("KISEKI_DATA_ROOT", "/from/env")
        assert resolve_paths(dotenv=tmp_path / ".env").data_root == Path("/from/env")

    def test_a_dotenv_file_wins_over_a_toml_file(self, tmp_path: Path) -> None:
        (tmp_path / "kiseki.toml").write_text(
            '[paths]\ndata_root = "/from/toml"\n', encoding="utf-8"
        )
        (tmp_path / ".env").write_text("KISEKI_DATA_ROOT=/from/dotenv\n", encoding="utf-8")
        assert resolve_paths(dotenv=tmp_path / ".env").data_root == Path("/from/dotenv")

    def test_a_toml_file_applies_where_nothing_else_does(self, tmp_path: Path) -> None:
        (tmp_path / "kiseki.toml").write_text(
            '[paths]\ndata_root = "/from/toml"\nlog_dir = "/logs"\n', encoding="utf-8"
        )
        (tmp_path / ".env").write_text("", encoding="utf-8")
        paths = resolve_paths(dotenv=tmp_path / ".env")
        assert paths.data_root == Path("/from/toml")
        assert paths.log_dir == Path("/logs")


class TestParsing:
    def test_comments_and_blank_lines_are_ignored(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text(
            "# a comment\n\nKISEKI_DATA_ROOT=/from/dotenv\n", encoding="utf-8"
        )
        assert resolve_paths(dotenv=tmp_path / ".env").data_root == Path("/from/dotenv")

    def test_quotes_are_stripped(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text(
            'KISEKI_DATA_ROOT="/from/dotenv"\n', encoding="utf-8"
        )
        assert resolve_paths(dotenv=tmp_path / ".env").data_root == Path("/from/dotenv")

    def test_a_missing_file_is_not_an_error(self, tmp_path: Path) -> None:
        assert resolve_paths(dotenv=tmp_path / "absent").data_root == Path.home() / ".kiseki"
