"""The gazetteer file follows the data root, or a name of its own."""

from pathlib import Path

from kiseki.config.paths import resolve_paths


def test_the_gazetteer_follows_the_root(tmp_path: Path) -> None:
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=None)
    assert paths.gazetteer_path == tmp_path / "gazetteer" / "cities500.txt"


def test_the_gazetteer_can_be_named_explicitly(tmp_path: Path) -> None:
    named = tmp_path / "geo" / "allCountries.txt"
    paths = resolve_paths({"data_root": str(tmp_path), "gazetteer_path": str(named)}, dotenv=None)
    assert paths.gazetteer_path == named
