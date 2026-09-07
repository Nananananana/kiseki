"""A document blurs unless the owner asks otherwise, whichever door it leaves by.

ADR-0026 promised that the served payloads and the command line share
one module "so the two interfaces cannot drift apart". They had. Seven
payloads defaulted to `blur=False` and seven `--json` commands took the
default, so `kiseki report --json` wrote the owner's anchors -- the
places returned to at night, which is to say home -- at full float
precision, about a centimetre, while `GET /report` blurred them to two
decimals. No test noticed either way: flipping every default changed
nothing in this suite.

The two tests that matter are the first two. One is structural, so a
payload added later cannot fail open; one is empirical on a library
with a known doorstep in it, because that is the failure as it actually
happened.
"""

import inspect
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.store import (
    SqlitePhotoRepository,
    SqliteProfileRepository,
    connect,
)
from kiseki.application.pipeline import Report
from kiseki.config.paths import resolve_paths
from kiseki.domain.analytics.analytics import PlacePreference, Rhythm
from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence, Profile
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.time_range import TimeRange
from kiseki.interfaces import payloads
from kiseki.interfaces.cli import EXIT_OK, main
from kiseki.interfaces.payloads import BLUR_DECIMALS, report_payload

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)
DOORSTEP = GeoPoint(35.011637, 135.768123)
EXACT = "35.011637,135.768123"
PLACE = "place:35.01"
"""Precise on purpose: every digit after the second decimal is the part
that must not leave."""


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def _seed_nights(tmp_path: Path) -> None:
    """Twenty nights at one point, which is what makes an anchor."""
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    at_night = WHEN.replace(hour=23, minute=30)
    SqlitePhotoRepository(connection).save_all(
        [
            PhotoObservation(
                photo_id=PhotoId(f"sha256:{day:02d}{shot}"),
                captured_at=at_night + timedelta(days=day, minutes=shot * 20),
                location=GeoPoint(DOORSTEP.latitude + shot * 1e-5, DOORSTEP.longitude),
            )
            for day in range(20)
            for shot in range(3)
        ]
    )
    connection.close()
    main(["--data-root", str(tmp_path), "build"])


def _seed(tmp_path: Path) -> None:
    """Two kept readings a month apart, whose one topic is a place.

    Two, because a trend, a lifecycle and a comparison each need a
    baseline to be anything at all."""
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    connection = connect(paths.db_path)
    repository = SqliteProfileRepository(connection)
    for days, score in ((0, 0.4), (30, 0.9)):
        at = WHEN + timedelta(days=days)
        repository.save(
            Profile(
                generated_at=at,
                interests=(
                    Interest(
                        topic=f"place:{EXACT}",
                        score=score,
                        confidence=0.9,
                        evidence=(
                            InterestEvidence(
                                kind=EvidenceKind.PHOTOGRAPH,
                                reference=f"place:{EXACT}",
                                observed_at=at,
                            ),
                        ),
                        first_seen=at,
                        last_seen=at,
                    ),
                ),
            )
        )
    connection.close()


def _anchor() -> Anchor:
    return Anchor(
        area=GeoArea(DOORSTEP, Distance(120)),
        period=TimeRange(WHEN, WHEN + timedelta(days=84)),
        visit_days=12,
        night_days=12,
        weekday_days=12,
        daytime_days=0,
        photograph_count=60,
        confidence=Confidence(0.9, 12),
    )


class TestNoPayloadFailsOpen:
    def test_every_payload_that_can_blur_blurs_by_default(self) -> None:
        """Structural, so a payload written next year cannot fail open.

        The safe direction is the default and the owner opts out, which
        is the shape `--raw` already had on the commands that got it
        right.
        """
        open_by_default = []
        for name, function in vars(payloads).items():
            if not name.endswith("_payload") or not callable(function):
                continue
            parameter = inspect.signature(function).parameters.get("blur")
            if parameter is not None and parameter.default is False:
                open_by_default.append(name)
        assert not open_by_default, open_by_default


class TestTheAnchorsAreNotHandedOut:
    """The failure as it happened: `kiseki report --json` and the
    owner's doorstep."""

    def test_the_written_report_carries_no_finer_place_than_the_blur(self) -> None:
        document = report_payload(_report_with_an_anchor())
        anchor = document["anchors"][0]
        assert anchor["latitude"] == round(DOORSTEP.latitude, BLUR_DECIMALS)
        assert anchor["longitude"] == round(DOORSTEP.longitude, BLUR_DECIMALS)

    def test_no_digit_of_the_doorstep_survives_in_the_text(self) -> None:
        """Serialised, because a float that prints as 35.0116 is still
        35.011637 to a consumer that reads the number."""
        written = json.dumps(report_payload(_report_with_an_anchor()))
        assert "35.011637" not in written
        assert "135.768123" not in written

    def test_the_owner_can_still_ask_for_the_exact_place(self) -> None:
        anchor = report_payload(_report_with_an_anchor(), blur=False)["anchors"][0]
        assert anchor["latitude"] == DOORSTEP.latitude


class TestEveryDoorAsksTheSameWay:
    COMMANDS = ("report", "profile", "trend", "lifecycle", "insights", "compare", "discover")
    """The seven that wrote raw documents with no way to ask for less."""

    @pytest.mark.parametrize("command", COMMANDS)
    def test_the_command_offers_raw_rather_than_only_doing_it(
        self, command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Blurred is the default and `--raw` opts out, as `suggest`,
        `today`, `now` and `ask` already did. Before this, these seven
        were raw with no flag at all."""
        assert main(["--data-root", str(tmp_path), command, "--raw", "--json"]) == EXIT_OK
        capsys.readouterr()

    @pytest.mark.parametrize("command", COMMANDS)
    def test_the_written_document_is_a_document(
        self, command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), command, "--json"]) == EXIT_OK
        json.loads(capsys.readouterr().out)


class TestTheReportCommandOnARealLibrary:
    """The leak exactly as it happened, through the command.

    Twenty nights of photographs at one point make an anchor, and
    an anchor visited at night is a home. Nothing shorter than this
    catches a command that hardcodes `blur=False`: the payload
    tests above still pass when it does.
    """

    def test_the_written_report_rounds_the_anchor(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed_nights(tmp_path)
        capsys.readouterr()
        assert main(["--data-root", str(tmp_path), "report", "--json"]) == EXIT_OK
        found = json.loads(capsys.readouterr().out)["anchors"]
        assert found, "no anchor was built, so this proves nothing"
        for place in found:
            for axis in ("latitude", "longitude"):
                assert place[axis] == round(place[axis], BLUR_DECIMALS), place

    def test_the_owner_can_still_ask_for_the_doorstep(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """And the test can tell the difference, which is the point."""
        _seed_nights(tmp_path)
        capsys.readouterr()
        code = main(["--data-root", str(tmp_path), "report", "--json", "--raw"])
        assert code == EXIT_OK
        found = json.loads(capsys.readouterr().out)["anchors"][0]
        assert found["latitude"] != round(found["latitude"], BLUR_DECIMALS)


class TestNoCommandHandsOutThePlace:
    """The end-to-end form, on a library whose one topic is a place.

    The first version of this class checked that `--raw` was
    accepted and that the output parsed, on an *empty* library.
    Both passed with the command hardcoding `blur=False`, which is
    the original defect written a second way. A library with a
    doorstep in it cannot be fooled that way.
    """

    CARRIES_A_TOPIC = (
        "trend",
        "lifecycle",
        "compare",
    )
    """The three that read kept profiles, so seeding two reaches them.

    `report` is covered above, with an anchor, which is the worse
    leak and the one that happened. `profile` derives a fresh
    reading from photographs rather than from kept readings, and
    `insights` and `discover` need evidence this fixture does not
    build; all three are held by the structural test instead,
    which is why that one is structural."""

    @pytest.mark.parametrize("command", CARRIES_A_TOPIC)
    def test_the_written_document_holds_no_finer_place(
        self, command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), command, "--json"]) == EXIT_OK
        written = capsys.readouterr().out
        assert PLACE in written, f"{command} said nothing about the place, so this proves nothing"
        assert EXACT not in written

    @pytest.mark.parametrize("command", CARRIES_A_TOPIC)
    def test_the_owner_can_still_ask_for_it(
        self, command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        assert main(["--data-root", str(tmp_path), command, "--json", "--raw"]) == EXIT_OK
        assert EXACT in capsys.readouterr().out


def _report_with_an_anchor() -> Report:
    """A library whose only place is the doorstep above."""
    return Report(
        photographs=60,
        anchors=(_anchor(),),
        outings=(),
        places=PlacePreference(places=(), return_rate=0.0, one_time_rate=0.0, most_returned_to=()),
        habits=None,
        rhythm=Rhythm(
            by_weekday={},
            by_departure_hour={},
            by_month={},
            weekend_share=0.0,
            early_start_share=0.0,
        ),
    )
