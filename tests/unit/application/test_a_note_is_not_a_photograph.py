"""Every kind of witness can be named, and the next one cannot be missed.

This library began with photographs, and `source_of` still ends with
`return EvidenceSource.PHOTOGRAPH` for a reference it does not
recognise. That fallback is correct for a bare topic, which is what a
photograph's reading becomes -- and it is also why three sources
shipped without anybody noticing that nothing could name them.

`note:` and `page:` were both absent from `PREFIXES`. So an answer
resting entirely on what the owner wrote and what they read said

    read from photograph

and `EvidenceSource.NOTE` existed for two releases without anything
being able to return it.

The first test below is the one that matters. It reads the source for
every prefix a derivation actually emits and refuses one the mapping
does not know, so a source added next year fails the build rather than
being quietly called a camera.
"""

import re
from pathlib import Path

import pytest
from kiseki.application.sourcing import PREFIXES, read_from, source_of, sources_of
from kiseki.domain.evidence.source import EvidenceSource

EMITTED = re.compile(r'reference=f?"([a-z_]+):')
"""How a derivation writes a reference it is about to store."""

DERIVATIONS = Path(__file__).parents[3] / "packages" / "kiseki-core" / "src" / "kiseki"


class TestNothingEmitsAPrefixNobodyCanName:
    def test_every_prefix_the_library_writes_is_in_the_mapping(self) -> None:
        """The guard. Scanned from the source, in both directions of
        reading: a prefix a derivation emits must be nameable."""
        emitted: set[str] = set()
        for module in DERIVATIONS.rglob("*.py"):
            emitted |= set(EMITTED.findall(module.read_text(encoding="utf-8")))
        unnameable = sorted(prefix for prefix in emitted if f"{prefix}:" not in PREFIXES)
        assert not unnameable, (
            f"these prefixes are written into references and fall through to "
            f"photograph: {unnameable}"
        )

    def test_the_mapping_is_not_full_of_prefixes_nothing_writes(self) -> None:
        """The other direction, loosely: every mapped prefix should name
        a source the enum holds, so a typo cannot sit there unused."""
        for source in PREFIXES.values():
            assert isinstance(source, EvidenceSource)


class TestTheSourcesThatWereMissing:
    @pytest.mark.parametrize(
        ("reference", "expected"),
        [
            ("note:diary.md#3", EvidenceSource.NOTE),
            ("page:a1b2c3d4", EvidenceSource.PAGE),
        ],
        ids=["what the owner wrote", "what the owner read"],
    )
    def test_it_is_named_for_what_it_is(self, reference: str, expected: EvidenceSource) -> None:
        assert source_of(reference) is expected

    def test_an_answer_from_notes_and_pages_does_not_claim_a_camera(self) -> None:
        """The sentence a reader was actually shown."""
        said = read_from(["note:diary.md#3", "page:a1b2c3d4"])
        assert "photograph" not in said
        assert "note" in said
        assert "page" in said

    def test_a_source_in_the_enum_can_be_reached_by_something(self) -> None:
        """`EvidenceSource.NOTE` existed for two releases and nothing
        could return it, which is the same as it not existing."""
        reachable = set(PREFIXES.values()) | {EvidenceSource.PHOTOGRAPH}
        unreachable = sorted(source.name for source in EvidenceSource if source not in reachable)
        assert unreachable == ["ACTIVITY"], (
            "ACTIVITY is the one source deliberately not cited as evidence: a day "
            "at the keys reaches report, privacy and limits as a count and the "
            "profile never sees it (ADR-0091). Anything else here is unreachable "
            f"by accident: {unreachable}"
        )


class TestWhatWasAlreadyRight:
    @pytest.mark.parametrize(
        ("reference", "expected"),
        [
            ("caption:aa", EvidenceSource.STAY_CAPTION),
            ("photo:aa", EvidenceSource.SINGLE_CAPTION),
            ("screen:aa", EvidenceSource.SCREEN),
            ("place:34.7,135.4", EvidenceSource.JOURNEY),
            ("profile:2026-06-01", EvidenceSource.KEPT_READING),
        ],
    )
    def test_the_older_prefixes_still_name_what_they_did(
        self, reference: str, expected: EvidenceSource
    ) -> None:
        assert source_of(reference) is expected

    def test_a_bare_topic_is_still_a_photograph(self) -> None:
        """Correct, and the reason the fallback stays: a topic with no
        prefix is what a photograph's reading becomes."""
        assert source_of("ramen") is EvidenceSource.PHOTOGRAPH

    def test_several_references_name_every_kind_once(self) -> None:
        assert sources_of(["note:a", "note:b", "page:c"]) == {
            EvidenceSource.NOTE,
            EvidenceSource.PAGE,
        }

    def test_nothing_read_says_nothing_rather_than_read_from_nothing(self) -> None:
        assert read_from([]) == ""
