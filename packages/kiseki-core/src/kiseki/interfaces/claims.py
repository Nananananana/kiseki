"""What holds however the library is configured, and what checks it.

Every line here is a claim, and every claim carries the name of the
test that fails if it stops being true. A README describes; this
specifies. The difference matters because a description drifts
silently and a specification turns a build red.

The claims are constant. What the models are told, where they are, and
what therefore leaves the machine is computed from the owner's own
configuration rather than asserted here -- see `outbound_lines`. A
privacy report that repeated the defaults would be answering about
somebody else's installation. See ADR-0074.
"""

from __future__ import annotations

from kiseki.config.model import ModelSettings
from kiseki.domain.trust import Locality

Claim = tuple[str, str, str]
"""A subject, what is true of it, and the test that keeps it true."""

TESTS = "tests/unit/test_privacy_promises.py"

NEVER_STORED: tuple[Claim, ...] = (
    (
        "screenshot text",
        "a reading is a category and labels; no text field exists (ADR-0030)",
        f"{TESTS}::test_a_screen_reading_has_nowhere_to_put_the_words",
    ),
    (
        "place names",
        "resolved from the owner's own gazetteer at display time (ADR-0040)",
        "tests/unit/interfaces/test_naming.py",
    ),
    (
        "anchor names",
        "anchors are never named (ADR-0040)",
        "tests/unit/domain/test_anchor.py",
    ),
    (
        "story-withheld records",
        "discarded at ingest, never stored (ADR-0032)",
        "tests/unit/interfaces/test_cli_ingest_consent.py",
    ),
    (
        "identifiers in the export",
        "no reference, no coordinate, no exact time ever leaves (ADR-0047)",
        f"{TESTS}::test_the_export_carries_no_identifier_no_place_no_timestamp",
    ),
    (
        "personal data in this repository",
        "no database and no image under packages or tests",
        f"{TESTS}::test_no_personal_data_is_committed",
    ),
)

BLURRED_BY_DEFAULT = (
    "served and written coordinates are rounded to about a kilometre"
    " unless raw output is asked for explicitly (ADR-0026)"
)


def outbound_lines(settings: ModelSettings) -> tuple[tuple[str, str], ...]:
    """Where things go, computed from this installation's settings.

    The library used to say "nothing is sent anywhere; no network call
    exists", which stopped being true the day captioning was written:
    a reduced copy of a photograph travels to the model in an HTTP
    body. It was localhost, so nothing left the machine, and the
    sentence was wrong about the mechanism while being right about the
    outcome. Now that the model may be elsewhere, the outcome has to
    be computed rather than asserted (ADR-0073).
    """
    verdict = settings.verdict
    where = {
        Locality.LOOPBACK: "this machine",
        Locality.PRIVATE: "a machine on your network",
        Locality.PUBLIC: "a machine on the internet",
        Locality.UNKNOWN: "a machine this library cannot place",
    }[verdict.locality]
    lines = [
        ("model host", settings.host),
        ("which is", where),
        ("boundary", settings.boundary.value),
    ]
    if settings.trusted_hosts:
        lines.append(("hosts you named", ", ".join(settings.trusted_hosts)))
    if verdict.locality is Locality.LOOPBACK:
        lines.append(("photographs", "go to the model on this machine, and nowhere else"))
    else:
        lines.append(
            (
                "photographs",
                f"a reduced copy is sent to {verdict.host} when captioning",
            )
        )
    lines.append(("everything else", "is never sent anywhere"))
    return tuple(lines)
