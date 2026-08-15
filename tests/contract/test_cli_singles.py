"""The singles command exists and is safe on an empty database."""

from kiseki.interfaces.cli import main


def test_singles_runs_against_an_empty_database(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["--data-root", str(tmp_path / "data"), "singles"])
    output = capsys.readouterr().out
    assert code == 0
    assert "captioned" in output
