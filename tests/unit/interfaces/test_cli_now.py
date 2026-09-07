"""One screen instead of six commands (ADR-0093).

Four regions, each a derivation the library already has, and every
empty one saying which command would fill it.
"""

import json
import os
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import (
    SqlitePhotoRepository,
    SqliteProfileRepository,
    SqliteSingleCaptionRepository,
    connect,
)
from kiseki.application.limits import LimitsReport
from kiseki.application.now import REGIONS, what_is_happening
from kiseki.application.today import OVERDUE, Today
from kiseki.config.paths import resolve_paths
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.interests import Profile
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.interfaces.cli import EXIT_OK, main
from kiseki.interfaces.payloads import now_payload

BASE = datetime(2026, 6, 1, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _gazetteer(tmp_path: Path) -> None:
    """A one-line gazetteer, so a missing file is not the fault
    every test here trips over."""
    where = tmp_path / "gazetteer"
    where.mkdir(parents=True, exist_ok=True)
    (where / "cities500.txt").write_text(
        chr(9).join(["1", "Osaka", "Osaka", "", "34.69", "135.50"] + [""] * 13) + chr(10),
        encoding="utf-8",
    )


def _run(tmp_path: Path, *rest: str) -> int:
    return main(["--data-root", str(tmp_path), "now", *rest])


def _connection(tmp_path: Path):
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    return connect(paths.db_path)


class TestTheWholeScreen:
    def test_every_region_is_on_it(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _gazetteer(tmp_path)
        assert _run(tmp_path) == EXIT_OK
        out = capsys.readouterr().out
        for region in REGIONS:
            assert region.name in out

    def test_an_empty_region_says_which_command_would_fill_it(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The difference between nothing to show and nothing was read."""
        _gazetteer(tmp_path)
        assert _run(tmp_path) == EXIT_OK
        out = capsys.readouterr().out
        assert "kiseki build" in out
        assert "kiseki profile --keep" in out

    def test_the_document_names_itself_and_carries_what_is_unread(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _gazetteer(tmp_path)
        assert _run(tmp_path, "--json") == EXIT_OK
        document = json.loads(capsys.readouterr().out)
        assert document["schema"] == "kiseki-now"
        assert set(document["unread"]) <= {region.name for region in REGIONS}
        assert "worth a look" in document["unread"]
        assert "what is thin" not in document["unread"], (
            "an empty library is thin, which is a reading rather than a gap"
        )


class TestAPlaceOnTheScreenIsBlurred:
    """Coordinates are the owner's. ADR-0026, applied to a screen."""

    def test_a_topic_that_is_a_place_is_rounded(self, tmp_path: Path) -> None:
        screen = what_is_happening(
            at=BASE,
            today=(
                Today(
                    kind=OVERDUE,
                    topic="place:34.756612,135.461234",
                    why_today="645 days since you were last there",
                    source="kiseki suggest",
                ),
            ),
            trends=None,
            limits=LimitsReport(sources=(), limits=()),
            wrong=(),
            photographs=0,
            outings=0,
        )
        blurred = now_payload(screen)["today"][0]["topic"]
        assert blurred == "place:34.76,135.46"
        assert now_payload(screen, blur=False)["today"][0]["topic"] == (
            "place:34.756612,135.461234"
        )


class TestItNeverReachesAModel:
    def test_a_socket_that_would_raise_does_not_stop_the_screen(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The screen that works on a machine where the model is away.

        Every request the library can make goes through one call, and
        here it raises. A `now` that reached a model would fail rather
        than answer, which is the state v0.11 spent a version fixing."""

        def refuse(*args: object, **kwargs: object) -> None:
            raise AssertionError("the screen opened a socket")

        monkeypatch.setattr(urllib.request, "urlopen", refuse)
        _gazetteer(tmp_path)
        assert _run(tmp_path) == EXIT_OK


class TestWhatIsWrongIsWhatDoctorFound:
    """One list, two renderings: they cannot disagree."""

    def test_a_library_with_no_kept_profile_says_so_on_both(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _gazetteer(tmp_path)
        assert _run(tmp_path) == EXIT_OK
        screen = capsys.readouterr().out
        assert main(["--data-root", str(tmp_path), "doctor"]) == EXIT_OK
        doctor = capsys.readouterr().out
        assert "no kept profile yet" in screen
        assert "no kept profile yet" in doctor

    def test_a_photograph_with_no_reduced_copy_reaches_the_screen(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        connection = _connection(tmp_path)
        SqlitePhotoRepository(connection).save_all(
            [
                PhotoObservation(
                    photo_id=PhotoId("sha256:aa"),
                    captured_at=BASE,
                    thumbnail_ref="aa.jpg",
                )
            ]
        )
        SqliteProfileRepository(connection).save(Profile(generated_at=BASE, interests=()))
        connection.close()
        _gazetteer(tmp_path)
        assert _run(tmp_path) == EXIT_OK
        assert "no reduced copy" in capsys.readouterr().out

    def test_a_sound_library_says_nothing_is_wrong_rather_than_staying_blank(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        connection = _connection(tmp_path)
        SqliteSingleCaptionRepository(connection).save(
            SingleCaption(PhotoId("sha256:aa"), "a bowl of ramen", "vl", BASE)
        )
        SqliteProfileRepository(connection).save(
            Profile(generated_at=BASE + timedelta(days=1), interests=())
        )
        connection.close()
        _gazetteer(tmp_path)
        assert _run(tmp_path) == EXIT_OK
        assert "nothing is wrong" in capsys.readouterr().out
