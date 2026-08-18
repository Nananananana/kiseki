"""The demo shows the whole engine without touching the owner's library."""

import os
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def test_every_derivation_speaks(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "sandbox"
    assert main(["demo", "--out", str(target)]) == EXIT_OK
    out = capsys.readouterr().out
    for heading in (
        "interests",
        "places",
        "lifecycle",
        "insights",
        "discover",
        "compare",
        "suggest",
    ):
        assert heading in out


def test_the_sandbox_is_swept_up(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "sandbox"
    assert main(["demo", "--out", str(target)]) == EXIT_OK
    assert not target.exists()


def test_keeping_it_says_where_it_is(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "sandbox"
    assert main(["demo", "--out", str(target), "--keep"]) == EXIT_OK
    assert target.is_dir()
    assert str(target) in capsys.readouterr().out


def test_the_configured_library_is_never_opened(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The demo reads no configuration: an .env cannot point it at real data."""
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / ".env").write_text(f"KISEKI_DATA_ROOT={real}\n", encoding="utf-8")
    assert main(["demo", "--out", str(tmp_path / "sandbox")]) == EXIT_OK
    assert list(real.iterdir()) == []


def test_the_suggestions_are_not_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A demo whose suggest says nothing teaches nothing."""
    assert main(["demo", "--out", str(tmp_path / "sandbox")]) == EXIT_OK
    out = capsys.readouterr().out
    assert "go back" in out
    assert "pick up" in out


def test_the_readings_become_interests(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demo", "--out", str(tmp_path / "sandbox")]) == EXIT_OK
    out = capsys.readouterr().out
    assert "ramen" in out.split("places")[0]


def test_a_day_trip_is_offered(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Somewhere inside the owner's own reach, quiet for long enough."""
    assert main(["demo", "--out", str(tmp_path / "sandbox")]) == EXIT_OK
    out = capsys.readouterr().out
    assert "day trip" in out
    assert "your outings cover under" in out


def test_the_far_place_is_not_offered(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The demo also contains somewhere far away, and it stays unmentioned."""
    assert main(["demo", "--out", str(tmp_path / "sandbox")]) == EXIT_OK
    out = capsys.readouterr().out
    trips = [line for line in out.splitlines() if "day trip" in line]
    assert len(trips) == 1
