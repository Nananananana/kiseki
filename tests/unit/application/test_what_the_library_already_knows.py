"""Grounding: the facts a derivation already produced.

`ask` retrieved captions and read them. Measured on a library with an
index built, before this existed:

    "where do I keep going back to?"
      -> "a place with an outdoor bath, as indicated by the steam
          over it [F3]"

    "am I going out less than last year?"
      -> "no evidence found for this question"

The first is the worse one. `kiseki places` held twelve visits about
every seven days; retrieval answered a question about a pattern by
searching captions for words. After this module, on the same library
and the same question:

    "You keep going back to two specific places, each visited on 12
     separate days between June 19 and September 4, 2026,
     approximately every six days [G1][G2]."

Two things this file exists to keep true, both learned by getting them
wrong on that first run.
"""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.application.grounding import (
    INTEREST,
    KINDS,
    PLACE,
    Grounding,
    from_anchors,
    from_outings,
    from_profile,
    numbered,
)
from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence, Profile
from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.time_range import TimeRange

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)
DOORSTEP = GeoPoint(35.0116, 135.7681)


def an_anchor(visit_days: int = 12) -> Anchor:
    return Anchor(
        area=GeoArea(DOORSTEP, Distance(120)),
        period=TimeRange(WHEN, WHEN + timedelta(days=84)),
        visit_days=visit_days,
        night_days=visit_days,
        weekday_days=visit_days,
        daytime_days=0,
        photograph_count=60,
        confidence=Confidence(0.9, visit_days),
    )


def an_interest(topic: str, score: float = 0.5) -> Interest:
    evidence = (
        InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference="caption:x", observed_at=WHEN),
    )
    return Interest(
        topic=topic,
        score=score,
        confidence=0.8,
        evidence=evidence,
        first_seen=WHEN,
        last_seen=WHEN,
    )


def an_outing(at: int) -> Outing:
    return Outing.of(
        [
            Stop(
                (PhotoId(f"sha256:{at:04d}"),),
                TimeRange(WHEN + timedelta(days=at), WHEN + timedelta(days=at, hours=2)),
                DOORSTEP,
            )
        ]
    )


class TestNoCoordinateEverReachesAPrompt:
    """The leak this module caused on its first run, and the rule it
    should have started with.

    A profile interest's topic can be a coordinate. Passing topics
    through unfiltered put two into a prompt and the model printed
    them back:

        ...if these locations align with the interests
        'place:35.01160,135.76810' and 'place:34.83500,135.46900'

    ADR-0047 says a place never leaves. `exporting.py` refuses these
    outright and `narrative.py` filters them before any prose; a
    prompt is a third way out, and it did not exist when either was
    written.
    """

    def test_a_place_interest_is_dropped(self) -> None:
        profile = Profile(
            generated_at=WHEN,
            interests=(an_interest("place:35.0116,135.7681", 0.9), an_interest("ramen", 0.5)),
        )
        facts = from_profile(profile)
        assert [fact.kind for fact in facts] == [INTEREST]
        assert "ramen" in facts[0].text

    def test_no_grounding_fact_carries_a_coordinate(self) -> None:
        """Across every builder at once, because the next one added
        will be added by somebody reading this file."""
        profile = Profile(
            generated_at=WHEN, interests=(an_interest("place:35.0116,135.7681", 0.9),)
        )
        facts = [
            *from_anchors([an_anchor()]),
            *from_profile(profile),
            *from_outings([an_outing(1)]),
        ]
        assert facts, "nothing was built, so this checks nothing"
        for fact in facts:
            assert "place:" not in fact.text
            assert "35.0116" not in fact.text
            assert "135.7681" not in fact.text

    def test_a_place_is_described_without_being_located(self) -> None:
        """What survives instead: the cadence and the shares, which is
        what ADR-0040 already decided an anchor is described by."""
        fact = from_anchors([an_anchor(12)])[0]
        assert "12 separate days" in fact.text
        assert "about every 7 days" in fact.text


class TestEveryFactNamesItsSource:
    """A grounding fact that cannot say where it came from is a claim
    the reader cannot go and check, which is the difference between
    this and a model's recollection."""

    def test_a_fact_with_no_source_is_refused(self) -> None:
        with pytest.raises(ValueError, match="cannot name its source"):
            Grounding(PLACE, "somewhere", "  ")

    def test_a_fact_with_no_text_is_refused(self) -> None:
        with pytest.raises(ValueError, match="says nothing"):
            Grounding(PLACE, "   ", "kiseki places")

    def test_a_kind_nobody_declared_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not a kind of grounding"):
            Grounding("vibes", "somewhere", "kiseki places")

    @pytest.mark.parametrize(
        ("build", "expected"),
        [
            (lambda: from_anchors([an_anchor()]), "kiseki places"),
            (lambda: from_outings([an_outing(1)]), "kiseki report"),
        ],
    )
    def test_each_builder_names_the_command_that_made_it(self, build, expected: str) -> None:  # type: ignore[no-untyped-def]
        facts = build()
        assert facts, "nothing was built, so this checks nothing"
        for fact in facts:
            assert fact.source == expected

    def test_every_kind_is_one_the_module_declares(self) -> None:
        profile = Profile(generated_at=WHEN, interests=(an_interest("ramen"),))
        facts = [
            *from_anchors([an_anchor()]),
            *from_profile(profile),
            *from_outings([an_outing(1)]),
        ]
        for fact in facts:
            assert fact.kind in KINDS


class TestNothingToStandOn:
    def test_no_anchors_yields_no_facts(self) -> None:
        assert from_anchors([]) == []

    def test_no_profile_yields_no_facts(self) -> None:
        assert from_profile(None) == []

    def test_no_outings_yields_no_facts(self) -> None:
        assert from_outings([]) == []

    def test_an_empty_library_grounds_nothing(self) -> None:
        """So `ask` still says it has nothing, rather than being handed
        an empty list it mistakes for knowledge."""
        assert [*from_anchors([]), *from_profile(None), *from_outings([])] == []


class TestTheClosedList:
    def test_facts_are_numbered_for_citation(self) -> None:
        text = numbered(from_anchors([an_anchor(), an_anchor(5)]))
        assert "[G1]" in text and "[G2]" in text

    def test_each_line_says_what_kind_it_is(self) -> None:
        """So the model can be told to prefer patterns for questions
        about habits, which is the whole point of the distinction."""
        assert f"({PLACE})" in numbered(from_anchors([an_anchor()]))

    def test_an_empty_list_is_an_empty_string(self) -> None:
        assert numbered([]) == ""
