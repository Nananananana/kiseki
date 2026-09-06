"""`narrate` returns the story with the closed list it was allowed to cite.

The facts were built for the prompt and thrown away after it, so a
footnote in the story pointed at nothing a client could show.
"""

from datetime import UTC, datetime

from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.application.narrative import build_prompt, narrate, tell
from kiseki.application.pipeline import Report
from kiseki.domain.analytics.analytics import summarise_places, summarise_rhythm
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence, Profile

WHEN = datetime(2026, 6, 1, tzinfo=UTC)


def _profile() -> Profile:
    evidence = (
        InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference="caption:x", observed_at=WHEN),
    )
    return Profile(
        generated_at=WHEN,
        interests=(
            Interest(
                topic="shrine",
                score=1.0,
                confidence=0.8,
                evidence=evidence,
                first_seen=WHEN,
                last_seen=WHEN,
            ),
        ),
    )


def _report() -> Report:
    return Report(
        photographs=3,
        outings=(),
        anchors=(),
        places=summarise_places((), None),
        rhythm=summarise_rhythm(()),
        habits=None,
    )


def test_the_facts_are_the_ones_the_prompt_numbered() -> None:
    model = FakeLanguageModel(answer=lambda system, prompt: "a story [F1]")
    narration = narrate(_profile(), _report(), model)
    _system, prompt = build_prompt(_profile(), _report(), "ja")
    for label, fact in narration.numbered:
        assert f"[{label}] {fact}" in prompt


def test_the_story_is_what_tell_returned() -> None:
    model = FakeLanguageModel(answer=lambda system, prompt: "a story [F1]")
    assert narrate(_profile(), _report(), model).story == tell(_profile(), _report(), model)


def test_a_subject_fact_is_among_them() -> None:
    model = FakeLanguageModel(answer=lambda system, prompt: "a story")
    narration = narrate(_profile(), _report(), model)
    assert any("shrine" in fact for fact in narration.facts)
