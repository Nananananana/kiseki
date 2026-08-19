"""The promises, checked by machine rather than by memory.

Every claim in the README's privacy section is either enforced somewhere
in code or it is decoration. These tests are where the difference is
kept: each one fails if a promise is broken, including by a future
change that meant no harm. See ADR-0059.
"""

import socket
from pathlib import Path

import pytest
from kiseki.application.exporting import interest_export
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.interfaces.cli import EXIT_OK, main
from kiseki.interfaces.payloads import BLUR_DECIMALS, NEVER_STORED

REPOSITORY = Path(__file__).resolve().parents[2]

FORBIDDEN_SUFFIXES = (
    ".sqlite3",
    ".db",
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".mov",
    ".mp4",
)

SEARCHED = ("packages", "tests")


class RefusedSocket(socket.socket):
    """A socket that cannot be opened, so an attempt is a test failure."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("KISEKI opened a socket; nothing should leave the machine")


def test_the_whole_engine_runs_without_a_socket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """kiseki demo builds, reads, derives and reports. None of it dials out."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket, "socket", RefusedSocket)
    monkeypatch.setattr(socket, "create_connection", _refuse)
    assert main(["demo", "--out", str(tmp_path / "sandbox")]) == EXIT_OK


def _refuse(*args: object, **kwargs: object) -> None:
    raise AssertionError("KISEKI opened a connection; nothing should leave the machine")


def test_a_screen_reading_has_nowhere_to_put_the_words() -> None:
    """ADR-0030 is kept by the type, not by the reader's restraint."""
    fields = set(ScreenshotReading.__dataclass_fields__)
    for forbidden in ("text", "body", "content", "words", "ocr"):
        assert forbidden not in fields


def test_the_export_carries_no_identifier_no_place_no_timestamp() -> None:
    """ADR-0047's forbidden list, checked against a profile that has all three."""
    from datetime import UTC, datetime

    from kiseki.domain.interests import (
        EvidenceKind,
        Interest,
        InterestEvidence,
        Profile,
    )

    when = datetime(2026, 6, 1, 12, 34, 56, tzinfo=UTC)
    evidence = (
        InterestEvidence(
            kind=EvidenceKind.PHOTOGRAPH,
            reference="caption:aaaaaaaabbbbbbbb",
            observed_at=when,
        ),
    )
    profile = Profile(
        generated_at=when,
        interests=(
            Interest(
                topic="ramen",
                score=0.6,
                confidence=0.5,
                evidence=evidence,
                first_seen=when,
                last_seen=when,
            ),
            Interest(
                topic="place:34.78100,135.46900",
                score=0.8,
                confidence=0.4,
                evidence=evidence,
                first_seen=when,
                last_seen=when,
            ),
        ),
    )
    document = interest_export(profile, None, when.date())
    text = str(document)
    assert "place:" not in text
    assert "34.78" not in text
    assert "caption:" not in text
    assert "aaaaaaaabbbbbbbb" not in text
    assert "12:34" not in text
    assert document["interests"][0]["first_seen"] == "2026-06"


def test_the_blur_is_about_a_kilometre() -> None:
    """A promise with a number in it deserves a test with the number in it."""
    assert BLUR_DECIMALS == 2


def test_the_privacy_report_still_names_what_is_never_stored() -> None:
    assert NEVER_STORED
    named = {name for name, _reason in NEVER_STORED}
    assert "screenshot text" in named
    assert "outbound copies" in named


def test_no_personal_data_is_committed() -> None:
    """The pre-commit hook refuses these; this refuses them again in CI."""
    offenders = []
    for folder in SEARCHED:
        root = REPOSITORY / folder
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
                offenders.append(str(path.relative_to(REPOSITORY)))
    assert offenders == []
