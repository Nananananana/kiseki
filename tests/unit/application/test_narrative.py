"""The narrative stage speaks only from a closed list of facts."""

from datetime import UTC, datetime

from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.narrative import build_prompt, narrative_facts, tell
from kiseki.application.pipeline import Pipeline, Report
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)

WHEN = datetime(2026, 5, 3, 10, tzinfo=UTC)
LATER = datetime(2026, 6, 3, 10, tzinfo=UTC)


def _report() -> Report:
    return Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
    ).report()


def _interest(topic: str, score: float = 0.6, confidence: float = 0.5) -> Interest:
    evidence = (
        InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference="caption:aa", observed_at=WHEN),
    )
    return Interest(
        topic=topic,
        score=score,
        confidence=confidence,
        evidence=evidence,
        first_seen=WHEN,
        last_seen=LATER,
    )


def _profile(*interests: Interest) -> Profile:
    return Profile(generated_at=WHEN, interests=tuple(interests))


class TestNarrativeFacts:
    def test_the_measures_come_first(self) -> None:
        facts = narrative_facts(_profile(), _report())
        assert "0 photographs" in facts[0]
        assert "0 outings" in facts[0]

    def test_a_subject_interest_becomes_a_fact(self) -> None:
        facts = narrative_facts(_profile(_interest("shrine")), _report())
        fact = facts[-1]
        assert "shrine" in fact
        assert "2026-05" in fact
        assert "2026-06" in fact
        assert "0.60" in fact
        assert "0.50" in fact

    def test_place_interests_stay_silent(self) -> None:
        facts = narrative_facts(_profile(_interest("place:35.00000,135.00000")), _report())
        assert not any("place:" in fact for fact in facts)

    def test_subjects_are_ranked_by_score_times_confidence(self) -> None:
        weak = _interest("weak", score=0.9, confidence=0.1)
        strong = _interest("strong", score=0.6, confidence=0.6)
        facts = narrative_facts(_profile(weak, strong), _report())
        strong_at = next(index for index, fact in enumerate(facts) if "strong" in fact)
        weak_at = next(index for index, fact in enumerate(facts) if "weak" in fact)
        assert strong_at < weak_at

    def test_the_subject_facts_are_capped(self) -> None:
        many = [_interest(f"topic-{index:02d}") for index in range(12)]
        facts = narrative_facts(_profile(*many), _report())
        subject_facts = [fact for fact in facts if "topic-" in fact]
        assert len(subject_facts) == 8


class TestBuildPrompt:
    def test_facts_are_numbered_for_citation(self) -> None:
        _, prompt = build_prompt(_profile(_interest("shrine")), _report(), "ja")
        assert "[F1]" in prompt
        assert "[F4]" in prompt

    def test_the_system_names_the_language(self) -> None:
        japanese, _ = build_prompt(_profile(), _report(), "ja")
        english, _ = build_prompt(_profile(), _report(), "en")
        assert "Japanese" in japanese
        assert "English" in english

    def test_an_unknown_language_falls_back_to_english(self) -> None:
        system, _ = build_prompt(_profile(), _report(), "xx")
        assert "English" in system


class TestTell:
    def test_hands_the_model_the_prompt_and_returns_its_words(self) -> None:
        model = FakeLanguageModel(
            answer=lambda system, prompt: f"facts:{prompt.count('[F')} ja:{'Japanese' in system}"
        )
        story = tell(_profile(_interest("shrine")), _report(), model, language="ja")
        assert story == "facts:4 ja:True"
