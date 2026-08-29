"""A root given on the command line outranks a path from a file."""

from pathlib import Path

from kiseki.config.paths import resolve_paths, set_aside


def _dotenv(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_flag_moves_everything(tmp_path: Path) -> None:
    """The fault: a corpus written into a real library, twice."""
    dotenv = _dotenv(
        tmp_path,
        "KISEKI_DATA_ROOT=/somewhere/real\nKISEKI_DB_PATH=/somewhere/real/db/kiseki.sqlite3\n",
    )
    paths = resolve_paths({"data_root": str(tmp_path / "sandbox")}, dotenv=dotenv)
    assert str(paths.db_path).startswith(str(tmp_path / "sandbox"))


def test_what_was_set_aside_can_be_said(tmp_path: Path) -> None:
    dotenv = _dotenv(
        tmp_path,
        "KISEKI_DB_PATH=/somewhere/real/db/kiseki.sqlite3\nKISEKI_LOG_DIR=/somewhere/real/logs\n",
    )
    displaced = set_aside({"data_root": str(tmp_path / "sandbox")}, dotenv=dotenv)
    assert set(displaced) == {"db_path", "log_dir"}


def test_within_one_layer_the_explicit_path_still_wins(tmp_path: Path) -> None:
    """A file that names both means both; nothing here changed."""
    dotenv = _dotenv(
        tmp_path,
        f"KISEKI_DATA_ROOT={tmp_path / 'root'}\n"
        f"KISEKI_DB_PATH={tmp_path / 'elsewhere' / 'kiseki.sqlite3'}\n",
    )
    paths = resolve_paths(dotenv=dotenv)
    assert paths.db_path == tmp_path / "elsewhere" / "kiseki.sqlite3"
    assert set_aside(dotenv=dotenv) == ()


def test_a_path_on_the_command_line_is_kept(tmp_path: Path) -> None:
    dotenv = _dotenv(tmp_path, "KISEKI_DATA_ROOT=/somewhere/real\n")
    paths = resolve_paths(
        {
            "data_root": str(tmp_path / "sandbox"),
            "db_path": str(tmp_path / "chosen.sqlite3"),
        },
        dotenv=dotenv,
    )
    assert paths.db_path == tmp_path / "chosen.sqlite3"


def test_an_environment_root_sets_aside_a_file_path(tmp_path: Path, monkeypatch: "object") -> None:
    """The environment is stronger than the files, and says so in the docstring."""
    import os

    dotenv = _dotenv(tmp_path, "KISEKI_DB_PATH=/from/a/file/kiseki.sqlite3\n")
    os.environ["KISEKI_DATA_ROOT"] = str(tmp_path / "from-env")
    try:
        paths = resolve_paths(dotenv=dotenv)
        assert str(paths.db_path).startswith(str(tmp_path / "from-env"))
    finally:
        del os.environ["KISEKI_DATA_ROOT"]
